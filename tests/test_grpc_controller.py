import asyncio

import pytest
from grpclib.testing import ChannelFor

from terraform import grpc_controller
from terraform.protos import grpc_controller_grpc, grpc_controller_pb2


@pytest.mark.asyncio
async def test_grpc_controller_shutdown():
    shutdown_event = asyncio.Event()
    service = grpc_controller.GRPCController(shutdown_event=shutdown_event)

    async with ChannelFor([service]) as channel:
        stub = grpc_controller_grpc.GRPCControllerStub(channel)

        response = await stub.Shutdown(grpc_controller_pb2.Empty())
        assert response == grpc_controller_pb2.Empty()
        assert shutdown_event.is_set()
