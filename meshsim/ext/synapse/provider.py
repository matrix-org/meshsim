import asyncio
import json
from quart import current_app
from tenacity import retry, wait_fixed, stop_after_attempt
from urllib.parse import quote

from ...provider import BaseProvider


class SynapseProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.room = None
        self.nodes_in_room = []

    async def start_node(self, id, host):
        proc = await asyncio.create_subprocess_exec(
            "./meshsim/scripts/synapse/start_node.sh", str(id), host
        )
        code = await proc.wait()
        if code != 0:
            raise Exception("Failed to start node")
        self.nodes.append(id)

    @retry(wait=wait_fixed(1))
    async def bootstrap(self):
        if self.room == None:
            await self.setup_room()

        for node_id in self.nodes:
            if not node_id in self.nodes_in_room:
                await self.join_room(node_id)
                self.nodes_in_room.append(node_id)

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(5))
    async def setup_room(self):
        creator_id = self.nodes[0]
        data = {'preset': "public_chat", 'room_alias_name': "test"}
        resp_raw = await self.post("http://localhost:%d/_matrix/client/r0/createRoom?access_token=fake_token" % (18000 + creator_id), data)
        resp = json.loads(resp_raw)
        current_app.logger.info(resp)
        self.room = resp

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(5))
    async def join_room(self, id):
        room = quote(self.room['room_alias'])
        resp_raw = await self.post("http://localhost:%d/_matrix/client/r0/join/%s?access_token=fake_token" % (18000 + id, room))
        resp = json.loads(resp_raw)
        current_app.logger.info(resp)
        if 'errcode' in resp:
            current_app.logger.info("Adf")
            raise RuntimeError("Could not join room")

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(5))
    async def send_message_from_node(self, id, message):
        data = {'body': message, 'msgtype': 'm.text'}
        current_app.logger.info(data)

        room = quote(self.room['room_id'])
        resp = await self.post("http://localhost:%d/_matrix/client/r0/rooms/%s/send/m.room.message?access_token=fake_token" % (18000 + id, room), data)
        current_app.logger.info(resp)
