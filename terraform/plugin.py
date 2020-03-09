import asyncio
import base64
import contextlib
import json
import logging
import os
import ssl
import sys
import tempfile
import typing

import grpclib.server
from grpclib.utils import graceful_exit

from terraform import diagnostics, schemas, settings, unknowns, utils
from terraform.grpc_controller import GRPCController
from terraform.protos import tfplugin5_1_grpc, tfplugin5_1_pb2

logger = logging.getLogger(__name__)


class ProviderService(tfplugin5_1_grpc.ProviderBase):
    def __init__(
        self,
        *,
        provider: schemas.Provider,
        shutdown_event: typing.Optional[asyncio.Event] = None,
    ):
        self.provider = provider
        self.shutdown_event = shutdown_event

    async def GetSchema(self, stream: grpclib.server.Stream) -> None:
        await stream.recv_message()

        response = tfplugin5_1_pb2.GetProviderSchema.Response(
            provider=tfplugin5_1_pb2.Schema(block=self.provider.to_block().to_proto()),
            resource_schemas={
                name: resource.to_proto()
                for name, resource in self.provider.resources.items()
            },
            data_source_schemas={
                name: resource.to_proto()
                for name, resource in self.provider.data_sources.items()
            },
        )
        await stream.send_message(response)

    async def PrepareProviderConfig(self, stream: grpclib.server.Stream) -> None:
        request = await stream.recv_message()

        config = utils.from_dynamic_value_proto(request.config)

        prepared_config = self.provider.dump(config)
        errors = self.provider.validate(prepared_config)
        provider_diagnostics = diagnostics.Diagnostics.from_schema_errors(errors)
        provider_diagnostics = provider_diagnostics.include_attribute_path_in_summary()

        response = tfplugin5_1_pb2.PrepareProviderConfig.Response(
            prepared_config=utils.to_dynamic_value_proto(prepared_config),
            diagnostics=provider_diagnostics.to_proto(),
        )
        await stream.send_message(response)

    async def ValidateResourceTypeConfig(self, stream: grpclib.server.Stream) -> None:
        request = await stream.recv_message()

        resource = self.provider.resources[request.type_name]
        config = utils.from_dynamic_value_proto(request.config)

        prepared_config = resource.dump(config)
        errors = resource.validate(prepared_config)
        resource_diagnostics = diagnostics.Diagnostics.from_schema_errors(errors)

        response = tfplugin5_1_pb2.ValidateResourceTypeConfig.Response(
            diagnostics=resource_diagnostics.to_proto()
        )
        await stream.send_message(response)

    async def ValidateDataSourceConfig(self, stream: grpclib.server.Stream) -> None:
        request = await stream.recv_message()

        resource = self.provider.data_sources[request.type_name]
        config = utils.from_dynamic_value_proto(request.config)

        prepared_config = resource.dump(config)
        errors = resource.validate(prepared_config)
        resource_diagnostics = diagnostics.Diagnostics.from_schema_errors(errors)

        response = tfplugin5_1_pb2.ValidateDataSourceConfig.Response(
            diagnostics=resource_diagnostics.to_proto()
        )
        await stream.send_message(response)

    async def UpgradeResourceState(self, stream: grpclib.server.Stream) -> None:
        pass

    async def Configure(self, stream: grpclib.server.Stream) -> None:
        request = await stream.recv_message()

        config = utils.from_dynamic_value_proto(request.config)
        self.provider.terraform_version = request.terraform_version or "0.11+compatible"
        self.provider.configure(config)

        response = tfplugin5_1_pb2.Configure.Response()
        await stream.send_message(response)

    async def ReadResource(self, stream: grpclib.server.Stream) -> None:
        pass

    async def PlanResourceChange(self, stream: grpclib.server.Stream) -> None:
        request = await stream.recv_message()

        resource = self.provider.resources[request.type_name]
        prior_state = utils.from_dynamic_value_proto(request.prior_state)
        proposed_new_state = utils.from_dynamic_value_proto(request.proposed_new_state)
        config = utils.from_dynamic_value_proto(request.config)
        prior_private = (
            json.loads(request.prior_private) if request.prior_private else None
        )

        destroy = proposed_new_state is None
        create = prior_state is None

        if destroy:
            planned_state = proposed_new_state
            planned_private = prior_private
        else:
            # TODO: implement me
            planned_state = proposed_new_state

            if create:
                planned_state = unknowns.set_unknowns(
                    planned_state, resource.to_block()
                )

            planned_private = prior_private

        response = tfplugin5_1_pb2.PlanResourceChange.Response(
            planned_state=utils.to_dynamic_value_proto(planned_state),
            planned_private=json.dumps(planned_private).encode("ascii"),
        )
        await stream.send_message(response)

    async def ApplyResourceChange(self, stream: grpclib.server.Stream) -> None:
        pass

    async def ImportResourceState(self, stream: grpclib.server.Stream) -> None:
        pass

    async def ReadDataSource(self, stream: grpclib.server.Stream) -> None:
        request = await stream.recv_message()

        resource = self.provider.data_sources[request.type_name]
        config = utils.from_dynamic_value_proto(request.config)
        data = schemas.ResourceData(config)

        await resource.read(data=data)

        if not data.get("id"):
            data.set_id("-")

        data = resource.dump(data)
        response = tfplugin5_1_pb2.ReadDataSource.Response(
            state=utils.to_dynamic_value_proto(dict(data))
        )
        await stream.send_message(response)

    async def Stop(self, stream: grpclib.server.Stream) -> None:
        pass


async def write_handshake_response(
    *,
    file: typing.TextIO,
    core_protocol_version: int = settings.CORE_PROTOCOL_VERSION,
    protocol_version: int,
    port: int,
    certificate,
):
    """
    Write the protocol versions, service name, address and certificate to the IO
    for the client.
    """
    certificate_der = utils.encode_certificate_der(certificate)
    certificate_b64 = base64.b64encode(certificate_der).decode("ascii").rstrip("=")

    file.write(
        "{}|{}|{}|{}|{}|{}\n".format(
            core_protocol_version,
            protocol_version,
            "tcp",
            f"127.0.0.1:{port}",
            "grpc",
            certificate_b64,
        )
    )
    file.flush()


async def wait_shutdown_event(
    *, server: grpclib.server.Server, shutdown_event: asyncio.Event
):
    """Wait for a shutdown event to close the server."""
    await shutdown_event.wait()
    server.close()


async def run_server(*, provider: schemas.Provider):
    if os.getenv(settings.MAGIC_COOKIE_KEY) != settings.MAGIC_COOKIE_VALUE:
        logger.error(
            "This is a Terraform plugin. "
            "These are not meant to be executed directly."
        )
        sys.exit(1)

    min_port = int(os.getenv("PLUGIN_MIN_PORT") or 0)
    max_port = int(os.getenv("PLUGIN_MAX_PORT") or 0)
    if min_port > max_port:
        logger.error("PLUGIN_MIN_PORT value is greater than PLUGIN_MAX_PORT value")
        sys.exit(1)

    certificate_data = utils.generate_certificate()
    with contextlib.ExitStack() as stack:
        keyfile = stack.enter_context(tempfile.NamedTemporaryFile())
        keyfile.write(utils.encode_private_key(certificate_data.private_key))
        keyfile.flush()
        certfile = stack.enter_context(tempfile.NamedTemporaryFile())
        certfile.write(utils.encode_certificate_pem(certificate_data.certificate))
        certfile.flush()

        client_cert = os.getenv("PLUGIN_CLIENT_CERT")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(certfile=certfile.name, keyfile=keyfile.name)
        ctx.load_verify_locations(cadata=client_cert)

        shutdown_event = asyncio.Event()

        handlers = [
            GRPCController(shutdown_event=shutdown_event),
            ProviderService(provider=provider, shutdown_event=shutdown_event),
        ]
        server = grpclib.server.Server(handlers)
        with graceful_exit([server]):
            port = min_port
            while port <= max_port:
                try:
                    await server.start("127.0.0.1", port, ssl=ctx)
                except OSError:
                    port += 1
                else:
                    break

            await write_handshake_response(
                file=sys.stdout,
                protocol_version=settings.PROTOCOL_VERSION,
                port=port,
                certificate=certificate_data.certificate,
            )
            await wait_shutdown_event(server=server, shutdown_event=shutdown_event)
            await server.wait_closed()


def run(*, provider: schemas.Provider):
    asyncio.run(run_server(provider=provider))
