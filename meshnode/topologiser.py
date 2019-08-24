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

import os
import sys
import json
from flask import Flask, request, abort, jsonify, send_from_directory
import subprocess
import requests
import psycopg2


abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

app = Flask(__name__, static_url_path='')


if (sys.version_info < (3, 5)):
    app.log.error("Needs Python 3.5 or later for subprocess.run()")
    exit

POSTGRES_USER = os.environ.get("POSTGRES_USER", "synapse")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "synapse")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "db")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", 5432)


def run(cmd):
    out = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    result = "\n>>> " + ' '.join(cmd)
    if out.stdout:
        result += "\n<<<\n" + out.stdout
    if out.stderr:
        result += "\n<!!\n" + out.stderr
    return result


@app.route("/routes", methods=["PUT"])
def set_routes():
    # [
    #   {
    #       dst: server,
    #       via: server
    #   }, ...
    # ]
    routes = request.get_json()

    dest_to_costs = {}

    result = ''
    result += run(["./clear_hs_routes.sh"])
    for route in routes:
        server_id = route['dst']['id']
        hostname = f"synapse{server_id}"

        dest_to_costs[hostname] = route["cost"]

        if route['via'] is None:
            continue

        result += run([
            "./add_hs_route.sh", route['dst']['ip'], route['via']['ip'],
        ])

    write_destination_health(dest_to_costs)

    return result

@app.route("/health", methods=["PUT"])
def set_network_health():
    # {
    #     peers: [
    #         {
    #             peer: <server>,
    #             bandwidth: 300, # 300bps
    #             latency: 200, # 200ms
    #             jitter: 20, # +/- 20ms - we apply 25% correlation on jitter
    #         }, ...
    #     ],
    #     clients: [
    #         {
    #             source_port: 54312,
    #             bandwidth: 300, # 300bps
    #             latency: 200, # 200ms
    #             jitter: 20, # +/- 20ms - we apply 25% correlation on jitter
    #         }, ...
    #     ]
    # }
    json = request.get_json()

    i = 2  # we start adding the queues from 1:2, as 1:1 is the default queue
    flow_count = len(json['peers']) + len(json['clients']) + 1
    if flow_count < 2:
        flow_count = 2

    result = ''
    result += run(
        ["./clear_hs_peer_health.sh", str(flow_count)]
    )
    for peer in json['peers']:
        mac = peer['peer']['mac'].split(":")
        result += run(
            ["./set_hs_peer_health.sh", str(i)] +
            mac +
            [str(peer['bandwidth']), str(peer['latency']), str(peer['jitter'])]
        )
        i = i + 1

    for client in json['clients']:
        result += run(
            ["./set_client_health.sh", str(i), str(client.get('source_port', 0))] +
            [str(client['bandwidth']), str(client['latency']), str(client['jitter'])]
        )

    return result

def write_destination_health(dest_to_cost):
    conn = psycopg2.connect(
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
    )
    with conn:
        with conn.cursor() as txn:
            txn.execute("TRUNCATE destination_health")
            for destination, cost in dest_to_cost.items():
                txn.execute(
                    "INSERT INTO destination_health VALUES (%s, %s)",
                    (destination, cost),
                )

    try:
        requests.get("http://localhost:8008/_matrix/client/r0/admin/server_health")
    except Exception as e:
        pass

app.run(host="0.0.0.0", port=3000, debug=True)
