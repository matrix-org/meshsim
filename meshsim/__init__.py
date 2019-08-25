# Copyright 2019 New Vector Ltd
#
# This file is part of meshsim.
#
# meshsim is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# meshsim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with coap-proxy.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import atexit
import json

from quart import Quart, abort, jsonify, request, send_from_directory, websocket, current_app
from logging.config import dictConfig
from math import sqrt
from secrets import token_urlsafe

from .mesh import Mesh
from .server import Server
from .ext.synapse import SynapseProvider


dictConfig({"version": 1, "loggers": {
           "quart.app": {"level": "INFO"}}})

app = Quart(__name__, static_folder="../frontend/static")


# We need to create this *after* start up so that it binds to correct event loop
event_notif_queue = None


@app.before_first_request
def setup_event_queue():
    global event_notif_queue
    event_notif_queue = asyncio.Queue()


@app.route("/")
def send_index():
    return send_from_directory("./frontend", "index.html")


@app.route("/server", methods=["POST"])
async def on_add_server():
    # {
    #   "x": 120,
    #   "y": 562
    # }
    incoming_json = await request.get_json()
    if not incoming_json:
        abort(400, "No JSON provided!")
        return

    x = incoming_json.get("x")
    y = incoming_json.get("y")

    server = await current_app.mesh.add_server(Server(x, y, app.node_provider))
    return jsonify({"id": server.id})


@app.route("/server/<server_id>/position", methods=["PUT"])
async def on_position_server(server_id):
    # {
    #   "x": 120,
    #   "y": 562
    # }
    server_id = int(server_id)
    incoming_json = await request.get_json()
    if not incoming_json:
        abort(400, "No JSON provided!")
        return

    x = incoming_json.get("x")
    y = incoming_json.get("y")

    server = current_app.mesh.get_server(server_id)
    await current_app.mesh.move_server(server, x, y)

    return ""


def name_to_id(name):
    return int(name.replace("meshsim-node", ""))


@app.route("/log", methods=["GET"])
async def on_incoming_log():
    args = request.args
    server = args["server"]
    msg = args["msg"]
    if msg == "ReceivedPDU":
        event_id = args["event_id"]
        origin = args["origin"]
        app.logger.info(f"Received {event_id}. {origin} -> {server}")
        await event_notif_queue.put(
            {
                "event_type": "receive",
                "source": origin,
                "target": server,
                "event": event_id,
            }
        )
    elif msg == "SendingPDU":
        event_id = args["event_id"]
        destinations = json.loads(args["destinations"])
        for destination in destinations:
            app.logger.info(
                f"{server} Sending {event_id}. {server} -> {destination}")
            await event_notif_queue.put(
                {
                    "event_type": "sending",
                    "source": server,
                    "target": destination,
                    "path": current_app.mesh.get_path(name_to_id(server), name_to_id(destination)),
                    "event": event_id,
                }
            )
    elif msg == "Libp2pReceive":
        event_id = args["event_id"]
        source_node_id = current_app.node_provider.peer_node_id(
            args["source"])
        source = f"meshsim-node{source_node_id}"
        app.logger.info(
            f"{server} Sending {event_id}. {source} -> {server}")
        await event_notif_queue.put(
            {
                "event_type": "receive",
                "source": source,
                "target": server,
                "event": event_id,
            }
        )

    return ""


@app.websocket("/event_notifs")
async def event_notifs():
    while True:
        msg = await event_notif_queue.get()
        await websocket.send(json.dumps(msg))


@app.route("/data", methods=["GET"])
def on_get_data():
    return current_app.mesh.get_d3_data()


@app.route("/costs", methods=["GET"])
def on_get_costs():
    return jsonify(current_app.mesh.get_costs())


@app.route("/defaults", methods=["GET"])
def on_get_defaults():
    return jsonify(current_app.mesh.get_defaults())


@app.route("/defaults", methods=["PUT"])
async def on_put_defaults():
    json = await request.get_json()
    current_app.mesh.set_defaults(json)
    await current_app.mesh.safe_rewire()
    return ""


@app.route("/messages", methods=["POST"])
async def on_send_messages():
    body = await request.get_json()
    node_ids = body.get('node_ids', [])
    message_size = int(body.get('message_size', 64))
    message = token_urlsafe(message_size)
    if not node_ids:
        return abort(422, description="No node ids provided")

    for node_id in node_ids:
        server = current_app.mesh.get_server(int(node_id))
        if not server:
            return abort(422, description="Invalid node id provided")
        await server.send_message(message)
    return ""


@app.route("/messages/bootstrap", methods=["POST"])
async def on_messages_bootstrap():
    await current_app.mesh.bootstrap()
    return ""


@app.route("/link/<server1>/<server2>/<type>", methods=["PUT"])
async def on_put_link_health(server1, server2, type):
    json = await request.get_json()
    current_app.mesh.set_link_health(int(server1), int(server2), json)
    await current_app.mesh.safe_rewire()
    return ""


@app.route("/link/<server1>/<server2>/<type>", methods=["DELETE"])
async def on_delete_link_health(server1, server2, type):
    json = {}
    json[type] = None
    current_app.mesh.set_link_health(int(server1), int(server2), json)
    await current_app.mesh.safe_rewire()
    return ""


@app.before_first_request
def setup_cleanup():
    atexit.register(cleanup)


def cleanup():
    app.node_provider.stop_clean_all()
