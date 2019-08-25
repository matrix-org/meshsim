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

import os
import sys
import json
from quart import Quart, request, abort, jsonify, send_from_directory


abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
TOPOLOGISER_MODE = os.getenv('TOPOLOGISER_MODE')
if TOPOLOGISER_MODE == "synapse":
    from provider.ext.synapse.provider import SynapseProvider
    provider = SynapseProvider()
elif TOPOLOGISER_MODE == "libp2p":
    from provider.ext.libp2p.provider import Libp2pProvider
    provider = Libp2pProvider()
else:
    raise ValueError(
        "Unsupported or missing topologiser mode: {}".format(TOPOLOGISER_MODE))

app = Quart(__name__, static_url_path='')
provider_blueprint = provider.blueprint()
if provider_blueprint:
    app.register_blueprint(provider_blueprint)


if (sys.version_info < (3, 5)):
    app.log.error("Needs Python 3.5 or later for subprocess.run()")
    exit


@app.route("/routes", methods=["PUT"])
async def set_routes():
    # [
    #   {
    #       dst: server,
    #       via: server
    #   }, ...
    # ]
    routes = await request.get_json()
    return await provider.update_routes(routes)


@app.route("/health", methods=["PUT"])
async def set_network_health():
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
    health = await request.get_json()
    return provider.update_health(health)


app.run(host="0.0.0.0", port=3000, debug=True)
