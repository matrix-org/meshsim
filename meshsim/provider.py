import json
import asyncio
import aiohttp
import async_timeout
import subprocess

from quart import current_app


class BaseProvider():
    def __init__(self):
        self.nodes = []

    def init_client_health_host(self):
        subprocess.call(["./scripts/init_client_health_host.sh"])

    def stop_clean_all(self):
        subprocess.call(["./scripts/stop_clean_all.sh"])

    async def set_client_host_health(self, clients=[]):
        for client in clients:
            proc = await asyncio.create_subprocess_exec(
                "./scripts/set_client_health_host.sh",
                str(client["source_port"]),
                str(client["bandwidth"]),
                str(client["latency"]),
                str(client["jitter"]),
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            current_app.logger.info(
                "with host result for %s", stdout.decode().strip()
            )

    async def start_node(self, id, host):
        proc = await asyncio.create_subprocess_exec(
            "./scripts/start_hs.sh", str(id), host
        )
        code = await proc.wait()
        if code != 0:
            raise Exception("Failed to start node")
        self.nodes.append(id)

    async def stop_node(self, id):
        proc = await asyncio.create_subprocess_exec(
            "./scripts/stop_hs.sh", str(id)
        )
        code = await proc.wait()
        if code != 0:
            raise Exception("Failed to stop node")
        self.nodes.remove(id)

    async def get_node_ip(self, id):
        proc = await asyncio.create_subprocess_exec(
            "./scripts/get_hs_ip.sh", str(id), stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()

    async def get_node_mac(self, id):
        proc = await asyncio.create_subprocess_exec(
            "./scripts/get_hs_mac.sh", str(id), stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()

    async def set_node_routes(self, id, data):
        return await self.put("http://localhost:%d/routes" % (19000 + id), data)

    async def set_node_health(self, id, data):
        return await self.put("http://localhost:%d/health" % (19000 + id), data)

    def send_message_from_node(self, id, message):
        raise NotImplementedError()

    def bootstrap(self):
        raise NotImplementedError()

    async def put(self, url, payload={}):
        data = json.dumps(payload, indent=4)
        async with aiohttp.ClientSession() as session, async_timeout.timeout(30):
            async with session.put(
                url, data=data, headers={
                    "Content-type": "application/json"}
            ) as response:
                return await response.text()

    async def post(self, url, payload={}):
        data = json.dumps(payload, indent=4)
        async with aiohttp.ClientSession() as session, async_timeout.timeout(30):
            async with session.post(
                url, data=data, headers={
                    "Content-type": "application/json"}
            ) as response:
                return await response.text()
