#!/usr/bin/env python

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
import networkx as nx

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

    def connect(self, server, limit=None):
        if (limit and (len(self.neighbours) > limit or len(server.neighbours) > limit)):
            return False
        self.neighbours.append(server)
        server.neighbours.append(self)
        return True

    def reset_neighbours(self):
        self.neighbours = []

MAX_SERVERS = 200


def main():
    graph = nx.Graph()

    servers = []
    for i in range(0, MAX_SERVERS):
        server = Server()
        servers.append(server)
        graph.add_node(server.id)

    # first we wire anyone closer together than 200
    for i in range(0, MAX_SERVERS):
        for j in range(i+1, MAX_SERVERS):
            distance = servers[i].distance(servers[j]);
            if distance < 200:
                servers[i].connect(servers[j])

    # then we reset the wirings and rewire the closest 4 neighbours.
    # we do this in two phases as we need to have all the possible
    # neighbours in place from both 'i' and 'j' sides of the matrix before
    # we know which are actually closest.
    for i in range(0, MAX_SERVERS):
        server = servers[i]
        neighbours = { n.id: server.distance(n) for n in server.neighbours }
        server.reset_neighbours()
        for (j, distance) in sorted(neighbours.items(), key=lambda x: x[1])[0:4]:
            if servers[i].connect(servers[j], 4):
                graph.add_edge(i, j, weight=distance)

    paths = nx.shortest_path(graph, weight='weight')
    costs = nx.shortest_path_length(graph, weight='weight')

    data = {
        'nodes': [],
        'links': [],
        'costs': list(costs),
        'paths': {
            u: {
                v: paths[u][v][1] if len(paths[u][v])>1 else None
                for v in paths[u].keys()
            } for u in paths.keys()
        },
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

    print(json.dumps(data, sort_keys=True, indent=4))

main()
