import asyncio
from flask import Blueprint, request, jsonify

from ...provider import BaseProvider


class Libp2pProvider(BaseProvider):
    def __init__(self):
        self.connected_nodes = []

    def update_routes(self, routes):
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

        for node in self.connected_nodes:
            if node not in new_connected_nodes:
                self.disconnect_from(node)
        for node in new_connected_nodes:
            if node not in self.connected_nodes:
                self.connect_to(node)

        return result

    def connect_to(self, peer):
        # Protobuf fun
        pass

    def disconnect_from(self, peer):
        # Protobuf fun
        pass

    def subscribe(self, topic):
        # Protobuf fun
        return jsonify({'subscribed': topic})

    def send_message(self, message):
        # Protobuf fun
        return jsonify({'sent': message})

    def blueprint(self):
        libp2p = Blueprint('libp2p', __name__, url_prefix='/libp2p')

        @libp2p.route("/subscribe/<topic>", methods=["POST"])
        def subscribe(topic):
            return self.subscribe(topic)

        @libp2p.route("/messages", methods=["POST"])
        def message():
            # {
            #   message: message,
            #   topic: topic
            # }
            payload = request.get_json()
            return self.send_message(payload['message'])

        return libp2p
