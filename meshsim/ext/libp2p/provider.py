import asyncio

from ...provider import BaseProvider


class Libp2pProvider(BaseProvider):
    async def start_node(self, id, host):
        proc = await asyncio.create_subprocess_exec(
            "./scripts/libp2p/start_node.sh", str(id), host
        )
        code = await proc.wait()
        if code != 0:
            raise Exception("Failed to start node")
        self.nodes.append(id)
