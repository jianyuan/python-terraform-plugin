import typing

import pytest
from grpclib.testing import ChannelFor

from terraform import fields, plugin, utils
from terraform.protos import tfplugin5_1_grpc, tfplugin5_1_pb2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,input_config,expected_output_config",
    (
        pytest.param(
            plugin.Provider.from_dict({"foo": fields.String(optional=True)})(),
            {"foo": "bar"},
            {"foo": "bar"},
            id="prepare",
        ),
        pytest.param(
            plugin.Provider.from_dict(
                {"foo": fields.String(optional=True, default="default")}
            )(),
            {"foo": None},
            {"foo": "default"},
            id="default",
        ),
        pytest.param(
            plugin.Provider.from_dict(
                {"foo": fields.String(optional=True, default=lambda: "defaultfunc")}
            )(),
            {"foo": None},
            {"foo": "defaultfunc"},
            id="defaultfunc",
        ),
        pytest.param(
            plugin.Provider.from_dict(
                {"foo": fields.String(required=True, default=lambda: "defaultfunc")}
            )(),
            {"foo": None},
            {"foo": "defaultfunc"},
            id="defaultfunc required",
        ),
        pytest.param(
            plugin.Provider.from_dict({"foo": fields.String(required=True)})(),
            {"foo": 3},
            {"foo": "3"},
            id="incorrect type",
        ),
        pytest.param(
            plugin.Provider.from_dict(
                {"foo": fields.String(optional=True, default=True)}
            )(),
            {"foo": None},
            {"foo": "True"},
            id="incorrect default type",
        ),
        pytest.param(
            plugin.Provider.from_dict(
                {"foo": fields.Bool(optional=True, default="")}
            )(),
            {"foo": None},
            {"foo": False},
            id="incorrect default bool type",
        ),
        pytest.param(
            plugin.Provider.from_dict(
                {
                    "foo": fields.Bool(
                        optional=True, default="do not use", removed="don't use this",
                    ),
                }
            )(),
            {"foo": None},
            {"foo": None},
            id="deprecated default",
        ),
    ),
)
async def test_prepare_provider_config(
    provider: plugin.Provider,
    input_config: typing.Dict[str, typing.Any],
    expected_output_config: typing.Dict[str, typing.Any],
):
    service = plugin.ProviderService(provider=provider)

    async with ChannelFor([service]) as channel:
        stub = tfplugin5_1_grpc.ProviderStub(channel)
        request = tfplugin5_1_pb2.PrepareProviderConfig.Request(
            config=utils.to_dynamic_value_proto(input_config)
        )

        response = await stub.PrepareProviderConfig(request)
        assert (
            utils.from_dynamic_value_proto(response.prepared_config)
            == expected_output_config
        )
