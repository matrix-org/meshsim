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

from .requests import put


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
        from .config import config
        proc = await asyncio.create_subprocess_exec(
            "./start_hs.sh", str(self.id), config.host
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
        current_app.logger.info(
            "setting routes for %d: %s", self.id, data)

        r = await put("http://localhost:%d/routes" % (19000 + self.id), data)

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
        data = json.dumps(health, indent=4)
        current_app.logger.info(
            "setting health for %d: %s", self.id, data)

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
                current_app.logger.info(
                    "with host result for %d: %s", self.id, stdout.decode().strip()
                )

        r = await put("http://localhost:%d/health" % (19000 + self.id), data)

        current_app.logger.info("with result for %d: %s", self.id, r)

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
