#!/usr/bin/env python3

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

import argparse
import asyncio
import atexit
import json
import os
import subprocess
from contextlib import contextmanager
from itertools import combinations
from logging.config import dictConfig
from math import sqrt

import aiohttp
import async_timeout
import networkx as nx
from quart import Quart, abort, jsonify, request, send_from_directory, websocket
from tenacity import retry, wait_fixed

args = None

dictConfig({"version": 1, "loggers": {"quart.app": {"level": "INFO"}}})

app = Quart(__name__, static_folder="./frontend/static")


# We need to create this *after* start up so that it binds to correct event loop
event_notif_queue = None


@app.before_first_request
def setup():
    global event_notif_queue
    event_notif_queue = asyncio.Queue()


async def put(url, data):
    async with aiohttp.ClientSession() as session, async_timeout.timeout(30):
        async with session.put(
            url, data=data, headers={"Content-type": "application/json"}
        ) as response:
            return await response.text()


class Server(object):
    _id = 0

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.id = Server._id
        self.ip = None
        self.mac = None
        Server._id = Server._id + 1

        self.paths = None  # cache of shortest paths
        self.path_costs = None  # cache of shortest path costs

        self.neighbours = set()

    def toDict(self):
        return {"id": self.id, "ip": self.ip, "mac": self.mac}

    async def start(self):
        global args
        proc = await asyncio.create_subprocess_exec(
            "./start_hs.sh", str(self.id), args.host
        )
        code = await proc.wait()
        if code != 0:
            raise Exception("Failed to start HS")
        await self.update_network_info()

    async def update_network_info(self):
        proc = await asyncio.create_subprocess_exec(
            "./get_hs_ip.sh", str(self.id), stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        self.ip = stdout.decode().strip()

        proc = await asyncio.create_subprocess_exec(
            "./get_hs_mac.sh", str(self.id), stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        self.mac = stdout.decode().strip()

    @retry(wait=wait_fixed(1))
    async def set_routes(self, routes):
        # [
        #   {
        #       dst: server,
        #       via: server
        #   }, ...
        # ]
        data = json.dumps(routes, indent=4)
        app.logger.info("setting routes for %d: %s", self.id, data)

        r = await put("http://localhost:%d/routes" % (19000 + self.id), data)

        app.logger.info("Set route with result for %d: %s", self.id, r)

    @retry(wait=wait_fixed(1))
    async def set_network_health(self, health):
        # {
        #     peers: [
        #         {
        #             peer: <server>,
        #             bandwidth: 300, # 300bps
        #             latency: 200, # 200ms
        #             jitter: 20, # +/- 20ms - we apply 25% correlation on jitter
        #             loss: 0, # 0% packet loss
        #         }, ...
        #     ],
        #     clients: [
        #         {
        #             source_port: 54312,
        #             bandwidth: 300, # 300bps
        #             latency: 200, # 200ms
        #             jitter: 20, # +/- 20ms - we apply 25% correlation on jitter
        #             loss: 0, # 0% packet loss
        #         }, ...
        #     ]
        # }
        data = json.dumps(health, indent=4)
        app.logger.info("setting health for %d: %s", self.id, data)

        # only apply client health on the host side once (picking server 0 arbitrarily)
        if self.id == 0:
            for client in health.get("clients", []):
                proc = await asyncio.create_subprocess_exec(
                    "./set_client_health_host.sh",
                    str(client["source_port"]),
                    str(client["bandwidth"]),
                    str(client["latency"]),
                    str(client["jitter"]),
                    stdout=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                app.logger.info(
                    "with host result for %d: %s", self.id, stdout.decode().strip()
                )

        r = await put("http://localhost:%d/health" % (19000 + self.id), data)

        app.logger.info("with result for %d: %s", self.id, r)

    def stop(self):
        subprocess.call(["./stop_hs.sh", str(self.id)])

    def distance(self, server2):
        return sqrt((server2.x - self.x) ** 2 + (server2.y - self.y) ** 2)

    def connect(self, server2, limit=None):
        if limit and (len(self.neighbours) > limit or len(server2.neighbours) > limit):
            return False

        # app.logger.info("connecting %d to %d", self.id, server2.id)

        self.neighbours.add(server2)
        server2.neighbours.add(self)
        return True

    def reset_neighbours(self):
        # app.logger.info("resetting neighbours for %d", self.id)
        self.neighbours = set()


class Mesh:

    COST_MIN_LATENCY = "cost_min_latency"
    COST_MAX_BANDWIDTH = "cost_max_bandwidth"

    def __init__(self, host_ip):
        self.graph = nx.Graph()
        self.servers = {}

        self.rewiring = False
        self.pending_rewire = False

        # global defaults
        self.bandwidth = 512000
        self.decay_bandwidth = True
        self.latency_scale = 100
        self.max_latency = 300
        self.min_bandwidth = 0
        self.jitter = 0
        self.packet_loss = 0
        self.cost_function = Mesh.COST_MIN_LATENCY

        self.client_bandwidth = 512000
        self.client_latency = 0
        self.client_jitter = 0
        self.client_loss = 0

        # link overrides
        self.overrides = {}

        # Number of things that are about to call rewire. Don't bother rewiring
        # unless this is zero.
        self._about_to_rewire_functions = 0

    async def add_server(self, server):
        # we deliberately add the server asap so we can echo its existence
        # back to the UI. however, we have to deliberately ignore it from
        # wiring calculations given it hasn't yet started
        self.servers[server.id] = server
        self.graph.add_node(server.id)

        with self.will_rewire():
            await server.start()

        await self.safe_rewire()
        return server

    def get_server(self, server_id):
        return self.servers[server_id]

    async def move_server(self, server, x, y):
        server.x = x
        server.y = y
        await self.safe_rewire()

    async def remove_server(self, server):
        server.stop()
        self.graph.remove_node(server.id)

        await self.safe_rewire()

    async def safe_rewire(self):
        if self._about_to_rewire_functions:
            app.logger.info("Skipping rewire as one will be triggered")
            return

        if self.rewiring:
            # no point in stacking them up
            if self.pending_rewire:
                app.logger.info(
                    "Skipping rewire as one already happening and one already queued"
                )
            else:
                app.logger.info("Deferring rewire as one already happening")
            self.pending_rewire = True
            return

        self.rewiring = True

        try:
            await self._rewire()
        finally:
            self.rewiring = False
            if self.pending_rewire:
                self.pending_rewire = False
                await self.safe_rewire()

    async def _rewire(self):
        if self.cost_function == Mesh.COST_MIN_LATENCY:
            cost_function = self.get_latency
        elif self.cost_function == Mesh.COST_MAX_BANDWIDTH:
            cost_function = self.get_bandwidth_cost

        started_servers = {
            i: self.servers[i] for i in self.servers if self.servers[i].ip is not None
        }

        # only try to wire servers which have started up and have IPs
        for server in started_servers.values():
            # Uncomment if we want to recheck IP/mac addresses of the containers:
            # await server.update_network_info()

            server.reset_neighbours()
            self.graph.remove_edges_from(list(self.graph.edges()))

        # first we wire anyone closer together than our thresholds
        for server1, server2 in combinations(started_servers.values(), 2):
            latency = self.get_latency(server1, server2)
            bandwidth = self.get_bandwidth(server1, server2)

            if latency < self.max_latency and bandwidth > self.min_bandwidth:
                server1.connect(server2)

        # then we reset the wirings and rewire the closest 4 neighbours.
        # we do this in two phases as we need to have all the possible
        # neighbours in place from both 'i' and 'j' sides of the matrix before
        # we know which are actually closest.
        for server in started_servers.values():
            neighbour_costs = {
                s.id: cost_function(server, s) for s in server.neighbours
            }
            server.reset_neighbours()
            for (j, cost) in sorted(neighbour_costs.items(), key=lambda x: x[1])[0:4]:
                if server.connect(started_servers[j], 4):
                    self.graph.add_edge(server.id, j, weight=cost)

        self.paths = nx.shortest_path(self.graph, weight="weight")
        self.path_costs = dict(nx.shortest_path_length(self.graph, weight="weight"))

        # app.logger.info("calculated shortest paths as %r", self.paths)

        c = list(combinations(started_servers, 2))
        app.logger.info("combinations %r", c)

        futures = (
            # apply the network topology in terms of routing table
            [
                self.get_server(source_id).set_routes(
                    [
                        {
                            "dst": self.get_server(dest_id).toDict(),
                            "via": (
                                self.get_server(
                                    self.paths[source_id][dest_id][1]
                                ).toDict()
                                if len(self.paths[source_id].get(dest_id, [])) > 1
                                else None
                            ),
                            "cost": self.path_costs[source_id].get(dest_id),
                        }
                        for dest_id in started_servers
                        if source_id != dest_id
                    ]
                )
                for source_id in started_servers
            ]
            +
            # apply the network characteristics to the peers
            [
                self.get_server(i).set_network_health(
                    {
                        "peers": [
                            {
                                "peer": neighbour.toDict(),
                                "bandwidth": self.get_bandwidth(
                                    self.get_server(i), neighbour
                                ),
                                "latency": self.get_latency(
                                    self.get_server(i), neighbour
                                ),
                                "jitter": self.get_jitter(
                                    self.get_server(i), neighbour
                                ),
                                "packet_loss": self.get_packet_loss(
                                    self.get_server(i), neighbour
                                ),
                            }
                            for neighbour in self.get_server(i).neighbours
                        ],
                        "clients": [
                            {
                                "source_port": 0,  # FIXME once we support multiple clients
                                "bandwidth": self.client_bandwidth,
                                "latency": self.client_latency,
                                "jitter": self.client_jitter,
                                "loss": self.client_loss,
                            }
                        ],
                    }
                )
                for i in started_servers
            ]
        )

        await asyncio.gather(*futures)

    def get_bandwidth_cost(self, server1, server2):
        return 1 / self.get_bandwidth(server1, server2)

    def get_bandwidth(self, server1, server2):
        if server1.id > server2.id:
            tmp = server1
            server1 = server2
            server2 = tmp

        override = self.overrides.get(server1.id, {}).get(server2.id, None)
        if override and override.get("bandwidth") is not None:
            return override.get("bandwidth")

        if self.decay_bandwidth:
            distance = server1.distance(server2)
            return int(
                self.bandwidth
                * ((self.max_latency - server1.distance(server2)) / self.max_latency)
            )
        else:
            return self.bandwidth

    def get_latency(self, server1, server2):
        if server1.id > server2.id:
            tmp = server1
            server1 = server2
            server2 = tmp

        override = self.overrides.get(server1.id, {}).get(server2.id, None)
        if override and override.get("latency") is not None:
            return override["latency"] * (self.latency_scale / 100)

        return int(server1.distance(server2)) * (self.latency_scale / 100)

    def get_jitter(self, server1, server2):
        if server1.id > server2.id:
            tmp = server1
            server1 = server2
            server2 = tmp

        override = self.overrides.get(server1.id, {}).get(server2.id, None)
        if override and override.get("jitter") is not None:
            return override["jitter"]

        return self.jitter

    def get_packet_loss(self, server1, server2):
        if server1.id > server2.id:
            tmp = server1
            server1 = server2
            server2 = tmp

        override = self.overrides.get(server1.id, {}).get(server2.id, None)
        if override and override.get("packet_loss") is not None:
            return override["packet_loss"]

        return self.packet_loss

    def set_link_health(self, server1_id, server2_id, health):
        override = {}
        for t in ["bandwidth", "latency", "jitter", "packet_loss"]:
            if t in health:
                override[t] = int(health.get(t)) if health.get(t) is not None else None

        self.overrides.setdefault(server1_id, {}).setdefault(server2_id, {}).update(
            override
        )
        app.logger.info("link health overrides now %r", self.overrides)

    def get_d3_data(self):
        data = {"nodes": [], "links": []}

        # XXX: frontend relies on index in data.nodes matches the server ID
        for _, server in sorted(self.servers.items()):
            data["nodes"].append({"name": server.id, "x": server.x, "y": server.y})
            for neighbour in server.neighbours:
                if server.id < neighbour.id:
                    link = {
                        "source": server.id,
                        "target": neighbour.id,
                        "bandwidth": self.get_bandwidth(server, neighbour),
                        "latency": self.get_latency(server, neighbour),
                        "jitter": self.get_jitter(server, neighbour),
                        "packet_loss": self.get_packet_loss(server, neighbour),
                    }

                    overrides = self.overrides.get(server.id, {}).get(neighbour.id, {})
                    for override in overrides:
                        if overrides[override] is not None:
                            link.setdefault("overrides", {})[override] = True

                    data["links"].append(link)

        return json.dumps(data, sort_keys=True, indent=4)

    def get_costs(self):
        if not self.path_costs:
            self.path_costs = dict(nx.shortest_path_length(self.graph, weight="weight"))
        return self.paths_costs

    def get_path(self, origin, target):
        if not self.paths:
            self.paths = nx.shortest_path(self.graph, weight="weight")
        return self.paths[origin][target]

    def get_defaults(self):
        return {
            "bandwidth": self.bandwidth,
            "decay_bandwidth": self.decay_bandwidth,
            "max_latency": self.max_latency,
            "min_bandwidth": self.min_bandwidth,
            "jitter": self.jitter,
            "packet_loss": self.packet_loss,
            "cost_function": self.cost_function,
            "latency_scale": self.latency_scale,
            "client_latency": self.client_latency,
            "client_bandwidth": self.client_bandwidth,
            "client_jitter": self.client_jitter,
            "client_loss": self.client_loss,
        }

    def set_defaults(self, defaults):
        self.bandwidth = int(defaults.get("bandwidth", self.bandwidth))
        self.decay_bandwidth = bool(
            defaults.get("decay_bandwidth", self.decay_bandwidth)
        )
        self.max_latency = int(defaults.get("max_latency", self.max_latency))
        self.min_bandwidth = int(defaults.get("min_bandwidth", self.min_bandwidth))
        self.jitter = int(defaults.get("jitter", self.jitter))
        self.packet_loss = int(defaults.get("packet_loss", self.packet_loss))
        self.cost_function = defaults.get("cost_function", self.cost_function)
        self.latency_scale = int(defaults.get("latency_scale", self.jitter))
        self.client_latency = int(defaults.get("client_latency", self.client_latency))
        self.client_bandwidth = int(
            defaults.get("client_bandwidth", self.client_bandwidth)
        )
        self.client_jitter = int(defaults.get("client_jitter", self.client_jitter))
        self.client_loss = int(defaults.get("client_loss", self.client_loss))

    @contextmanager
    def will_rewire(self):
        try:
            self._about_to_rewire_functions += 1
            yield
        finally:
            self._about_to_rewire_functions -= 1


mesh = Mesh("")


@app.route("/")
def send_index():
    return send_from_directory("./frontend/", "index.html")

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

    server = await mesh.add_server(Server(x, y))
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

    server = mesh.get_server(server_id)
    await mesh.move_server(server, x, y)

    return ""


def name_to_id(name):
    return int(name.replace("synapse", ""))


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
            app.logger.info(f"{server} Sending {event_id}. {server} -> {destination}")
            await event_notif_queue.put(
                {
                    "event_type": "sending",
                    "source": server,
                    "target": destination,
                    "path": mesh.get_path(name_to_id(server), name_to_id(destination)),
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
    return mesh.get_d3_data()


@app.route("/costs", methods=["GET"])
def on_get_costs():
    return jsonify(mesh.get_costs())


@app.route("/defaults", methods=["GET"])
def on_get_defaults():
    return jsonify(mesh.get_defaults())


@app.route("/defaults", methods=["PUT"])
async def on_put_defaults():
    json = await request.get_json()
    mesh.set_defaults(json)
    await mesh.safe_rewire()
    return ""


@app.route("/link/<server1>/<server2>/<type>", methods=["PUT"])
async def on_put_link_health(server1, server2, type):
    json = await request.get_json()
    mesh.set_link_health(int(server1), int(server2), json)
    await mesh.safe_rewire()
    return ""


@app.route("/link/<server1>/<server2>/<type>", methods=["DELETE"])
async def on_delete_link_health(server1, server2, type):
    json = {}
    json[type] = None
    mesh.set_link_health(int(server1), int(server2), json)
    await mesh.safe_rewire()
    return ""


def cleanup():
    subprocess.call(["./stop_clean_all.sh"])


@app.before_first_request
def setup():
    atexit.register(cleanup)


def main():
    global args

    parser = argparse.ArgumentParser(description="Synapse network simulator.")
    parser.add_argument(
        "host", help="The IP address of this host in the docker network."
    )
    parser.add_argument(
        "--port",
        "-p",
        help="The port for meshsim to listen on",
        nargs=1,
        default=3000,
        type=int,
    )
    parser.add_argument(
        "--jaeger",
        "-j",
        help="Enable Jaeger tracing in Synapse and CoAP proxy",
        action="store_true",
    )
    parser.add_argument(
        "--no-proxy",
        "-n",
        help="Have Synapse talk directly to each other rather than via the CoAP proxy",
        action="store_false",
        dest="use_proxy",
    )
    parser.add_argument(
        "--proxy-dump-payloads",
        help="Debug option to make the CoAP proxy log the packets that are being sent/received",
        action="store_true",
    )
    args = parser.parse_args()

    host = args.host
    os.environ["POSTGRES_HOST"] = host
    os.environ["SYNAPSE_LOG_HOST"] = host

    if args.jaeger:
        os.environ["SYNAPSE_JAEGER_HOST"] = host

    if args.use_proxy:
        os.environ["SYNAPSE_USE_PROXY"] = "1"

    if args.proxy_dump_payloads:
        os.environ["PROXY_DUMP_PAYLOADS"] = "1"

    subprocess.call(["./init_client_health_host.sh"])
    app.run(host="0.0.0.0", port=args.port, debug=True)


if __name__ == "__main__":
    main()
