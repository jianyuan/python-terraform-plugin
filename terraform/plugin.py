import asyncio
import base64
import collections
import contextlib
import logging
import os
import ssl
import sys
import tempfile
import typing

import grpclib.server
from grpclib.utils import graceful_exit

from terraform import settings, utils
from terraform.grpc_controller import GRPCController

logger = logging.getLogger(__name__)


class BaseResource:
    name: str


class Resource(BaseResource):
    ...


class DataSource(BaseResource):
    ...


class Resources(collections.abc.Mapping):
    def __init__(
        self, resources: typing.Optional[typing.Sequence[BaseResource]] = None
    ):
        self.resources = [] if resources is None else list(resources)

    def __getitem__(self, name):
        for resource in self.resources:
            if resource.name == name:
                return resource
        raise KeyError(name)

    def __iter__(self):
        return iter(self.resources)

    def __len__(self):
        return len(self.resources)

    def add(self, resource: BaseResource):
        self.resources.append(resource)


class Provider:
    name: str

    def __init__(
        self,
        resources: typing.Optional[typing.Sequence[Resource]] = None,
        data_sources: typing.Optional[typing.Sequence[DataSource]] = None,
    ):
        self.resources = Resources(resources)
        self.data_sources = Resources(data_sources)

    def add_resource(self, resource: Resource):
        self.resources.add(resource)

    def add_data_source(self, data_source: DataSource):
        self.data_sources.add(data_source)


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


async def run_server(*, provider: Provider):
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


def run(*, provider: Provider):
    asyncio.run(run_server(provider=provider))
