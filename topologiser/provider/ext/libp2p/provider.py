import asyncio
import threading
from flask import Blueprint, request, jsonify

from ...provider import BaseProvider
from .p2pd_wrapper import P2PDWrapper


class Libp2pProvider(BaseProvider):
    def __init__(self):
        self.connected_nodes = []

    def p2pd(self):
        return P2PDWrapper()

    async def update_routes(self, routes):
        result = ''
        result += self.run(["./scripts/clear_hs_routes.sh"])
        new_connected_nodes = []
        for route in routes:
            server_id = route['dst']['id']
            hostname = f"meshsim-node{server_id}"
            new_connected_nodes.append(hostname)
            if route['via'] is None:
                continue

            result += self.run([
                "./scripts/add_hs_route.sh", route['dst']['ip'], route['via']['ip'],
            ])

        futures = []
        for node in self.connected_nodes:
            if node not in new_connected_nodes:
                futures.append(self.disconnect_from(node))
        for node in new_connected_nodes:
            if node not in self.connected_nodes:
                futures.append(self.connect_to(node))

        await asyncio.gather(*futures)
        return result

    async def connect_to(self, host):
        resp = await self.get("http://%s:%d/libp2p/identity" % (host, 3000))
        peer = json.loads(resp)
        return self.p2pd().connect(peer)

    async def disconnect_from(self, host):
        resp = await self.get("http://%s:%d/libp2p/identity" % (host, 3000))
        peer = json.loads(resp)
        return self.p2pd().disconnect(peer)

    def subscribe(self, topic):
        con = self.p2pd()
        resp = con.subscribe()

        async def _listen():
            while True:
                print("waiting for message")
                msg = con.next_pubsub_message()
                # make request to /log to signale recieved a message
                log_host = os.getenv('LOG_HOST')
                server = os.getenv('NODE_HOST')
                resp = await self.get("http://%s:%d/log?server=%s&msg=Libp2pReceive&source=%s" % (log_host, 3000, server, msg['source']))
                current_app.logger.info(resp)

        thread = threading.Thread(target=_listen)
        thread.start()

        return jsonify({'response': resp.type})

    def send_message(self, message):
        resp = self.p2pd().publish(message)
        return jsonify({'response': resp.type})

    async def get(self, url):
        async with aiohttp.ClientSession() as session, async_timeout.timeout(30):
            async with session.get(
                url, headers={
                    "Content-type": "application/json"}
            ) as response:
                return await response.text()

    def blueprint(self):
        libp2p = Blueprint('libp2p', __name__, url_prefix='/libp2p')

        @libp2p.route("/subscribe/<topic>", methods=["POST"])
        def subscribe(topic):
            identity = self.p2pd.identify()
            return self.subscribe(topic).update({'identity': identity})

        @libp2p.route("/messages", methods=["POST"])
        def message():
            # {
            #   message: message,
            #   topic: topic
            # }
            payload = request.get_json()
            return self.send_message(payload['message'])

        @libp2p.route("/identity", methods=["GET"])
        def identity():
            return self.p2pd().identify()

        return libp2p
