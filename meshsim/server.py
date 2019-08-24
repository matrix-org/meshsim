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

import json
import asyncio
import subprocess

from quart import current_app
from math import sqrt
from tenacity import retry, wait_fixed


class Server(object):
    _id = 0

    def __init__(self, x, y, provider):
        self.x = x
        self.y = y
        self.provider = provider
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
        await self.provider.start_node(self.id, current_app.config['ARGS'].host)
        await self.update_network_info()

    async def update_network_info(self):
        self.ip = await self.provider.get_node_ip(self.id)
        self.mac = await self.provider.get_node_mac(self.id)

    @retry(wait=wait_fixed(1))
    async def set_routes(self, routes):
        # [
        #   {
        #       dst: server,
        #       via: server
        #   }, ...
        # ]
        current_app.logger.info(
            "setting routes for %d: %s", self.id, json.dumps(routes, indent=4))
        r = await self.provider.set_node_routes(self.id, routes)

        current_app.logger.info(
            "Set route with result for %d: %s", self.id, r)

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
        current_app.logger.info(
            "setting health for %d: %s", self.id, json.dumps(health, indent=4))

        r = await self.provider.set_node_health(self.id, health)
        current_app.logger.info("with result for %d: %s", self.id, r)

    def stop(self):
        self.provider.stop_node(self.id)

    def distance(self, server2):
        return sqrt((server2.x - self.x) ** 2 + (server2.y - self.y) ** 2)

    def connect(self, server2, limit=None):
        if limit and (len(self.neighbours) > limit or len(server2.neighbours) > limit):
            return False

        # app.logger.info("connecting %d to %d", self.id, server2.id)

        self.neighbours.add(server2)
        server2.neighbours.add(self)
        return True

    async def send_message(self, message):
        await self.provider.send_message_from_node(self.id, message)

    def reset_neighbours(self):
        # app.logger.info("resetting neighbours for %d", self.id)
        self.neighbours = set()
