import os
import json
import aiohttp
import asyncio
import async_timeout
import threading
from tenacity import retry, wait_fixed, stop_after_attempt
from quart import Blueprint, request, jsonify, current_app

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
            current_app.logger.info(route)

            if route['via'] is None:
                continue

            if route['via']['id'] == server_id:
                # direct connection
                new_connected_nodes.append(hostname)

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

        self.connected_nodes = new_connected_nodes
        current_app.logger.info(
            f"Connected to: {new_connected_nodes}")

        return result

    async def connect_to(self, host):
        peer = await self.get_peer(host)
        resp = self.p2pd().connect(peer)
        current_app.logger.info(f"Connect to {host}: {resp}")
        return resp

    async def disconnect_from(self, host):
        peer = await self.get_peer(host)
        resp = self.p2pd().disconnect(peer)
        current_app.logger.info(f"Disconnect from {host}: {resp}")
        return resp

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(15))
    async def get_peer(self, host):
        resp = await self.get("http://%s:%d/libp2p/identity" % (host, 3000))
        return json.loads(resp)

    def subscribe(self, topic):
        con = self.p2pd()
        resp = con.subscribe(topic)

        def _listen(con, loop):
            async def run():
                while True:
                    print("waiting for messages")
                    msg = con.next_pubsub_message()
                    # make request to /log to signale recieved a message
                    log_host = os.getenv('LOG_HOST')
                    server = os.getenv('NODE_HOST')
                    print(f"{server}: recv from {msg['source']}")
                    resp = await self.get("http://%s:%d/log?server=%s&msg=Libp2pReceive&source=%s&event_id=%s" % (log_host, 3000, server, msg['source'], msg['event_id']))
            asyncio.set_event_loop(loop)
            asyncio.run(run())

        thread = threading.Thread(
            target=_listen, args=(con, asyncio.new_event_loop(),), daemon=True)
        current_app.logger.info("starting subscription thread")
        thread.start()
        # asyncio.create_task(_listen(con, current_app))

        return {'response': resp.type}

    def send_message(self, payload):
        resp = self.p2pd().publish(
            payload['topic'], payload['message'])
        current_app.logger.info(resp)
        return {'response': resp.type}

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
            resp = self.subscribe(topic)
            resp.update({'identity': self.p2pd().identify()})
            current_app.logger.info("Done subscribe")
            return jsonify(resp)

        @libp2p.route("/messages", methods=["POST"])
        async def message():
            # {
            #   message: message,
            #   topic: topic
            # }
            current_app.logger.info("Before get json")
            payload = await request.get_json()
            current_app.logger.info("Messages post")
            return jsonify(self.send_message(payload))

        @libp2p.route("/identity", methods=["GET"])
        def identity():
            return jsonify(self.p2pd().identify())

        return libp2p
