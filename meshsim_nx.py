#!/usr/bin/env python

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

    def connect(self, server):
        self.neighbours.append(server)


MAX_SERVERS = 200


def main():
    graph = nx.Graph()

    servers = []
    for i in range(0, MAX_SERVERS):
        server = Server()
        servers.append(server)
        graph.add_node(server.id)

    for i in range(0, MAX_SERVERS):
        for j in range(i+1, MAX_SERVERS):
            distance = servers[i].distance(servers[j]);
            if distance < 100:
                servers[i].connect(servers[j])
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

    print json.dumps(data, sort_keys=True, indent=4)

main()