import asyncio
import json
from quart import current_app
from tenacity import retry, wait_fixed, stop_after_attempt

from ...provider import BaseProvider


class Libp2pProvider(BaseProvider):
    def __init__(self):
        super().__init__()
        self.topic = "test-topic"
        self.subscribed_nodes = []
        self.node_identities = {}

    def peer_node_id(self, peer_id):
        for node_id in self.node_identities:
            if self.node_identities[node_id]['id'] == peer_id:
                return node_id
        return None

    async def start_node(self, id, host):
        proc = await asyncio.create_subprocess_exec(
            "./meshsim/scripts/libp2p/start_node.sh", str(id), host
        )
        code = await proc.wait()
        if code != 0:
            raise Exception("Failed to start node")
        self.nodes.append(id)

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(5))
    async def bootstrap(self):
        for node_id in self.nodes:
            if not node_id in self.subscribed_nodes:
                resp = await self.subscribe_to_topic(node_id)
                self.node_identities[node_id] = resp['identity']
                self.subscribed_nodes.append(node_id)

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(5))
    async def subscribe_to_topic(self, id):
        resp_raw = await self.post("http://localhost:%d/libp2p/subscribe/%s" % (19000 + id, self.topic))
        resp = json.loads(resp_raw)
        current_app.logger.info(resp)
        return resp

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(5))
    async def send_message_from_node(self, id, message):
        data = {'message': message, 'topic': self.topic}
        current_app.logger.info(data)
        resp = await self.post("http://localhost:%d/libp2p/messages" % (19000 + id), data)
        current_app.logger.info(resp)
