#!/usr/bin/python

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
from random import randint
from math import sqrt
from dijkstar import Graph, find_path

class Server:
    _id = 0

    def __init__(self):
        self.x = randint(0, 1000)
        self.y = randint(0, 1000)
        self.id = Server._id
        Server._id = Server._id + 1

        self.neighbours = []

    def distance(self, server):
        return sqrt((server.x - self.x)**2 + (server.y - self.y)**2)

    def connect(self, server):
        self.neighbours.append(server)


MAX_SERVERS = 200


def main():
    servers = []
    for i in range(0, MAX_SERVERS):
        servers.append(Server())

    graph = Graph()

    for i in range(0, MAX_SERVERS):
        for j in range(i+1, MAX_SERVERS):
            distance = servers[i].distance(servers[j]);
            if distance < 100:
                servers[i].connect(servers[j])
                graph.add_edge(i, j, {'cost': distance})

    data = {
        'nodes': [],
        'links': [],
    }

    for server in servers:
        data['nodes'].append({
            'name': server.id,
            'x': server.x,
            'y': server.y,
        })
        for neighbour in server.neighbours:
            data['links'].append({
                'source': server.id,
                'target': neighbour.id,
            })

    # cost_func = lambda u, v, e, prev_e: e['cost']
    # for i in range(0, MAX_SERVERS):
    #     for j in range(i+1, MAX_SERVERS):
    #         path = find_path(graph, i, j, cost_func=cost_func)
    #         data['costs'][i][j]

    print json.dumps(data, sort_keys=True, indent=4)

main()