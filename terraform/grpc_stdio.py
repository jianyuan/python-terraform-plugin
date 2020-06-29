import typing

from terraform.protos import grpc_stdio_grpc

if typing.TYPE_CHECKING:
    import grpclib.server


class GRPCStdio(grpc_stdio_grpc.GRPCStdioBase):
    async def StreamStdio(self, stream: "grpclib.server.Stream") -> None:
        ...
