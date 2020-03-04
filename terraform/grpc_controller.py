import asyncio
import typing

from terraform.protos import grpc_controller_grpc, grpc_controller_pb2

if typing.TYPE_CHECKING:
    import grpclib.server


class GRPCController(grpc_controller_grpc.GRPCControllerBase):
    def __init__(self, *, shutdown_event: asyncio.Event):
        self.shutdown_event = shutdown_event

    async def Shutdown(self, stream: "grpclib.server.Stream"):
        await stream.recv_message()

        self.shutdown_event.set()

        await stream.send_message(grpc_controller_pb2.Empty())
