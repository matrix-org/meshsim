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
import argparse

from meshsim import app
from meshsim.mesh import Mesh


def main():
    parser = argparse.ArgumentParser(
        description="Mesh network simulator.")
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
        help="Enable Jaeger tracing in Node and CoAP proxy",
        action="store_true",
    )
    parser.add_argument(
        "--no-proxy",
        "-n",
        help="Have nodes talk directly to each other rather than via the CoAP proxy",
        action="store_false",
        dest="use_proxy",
    )
    parser.add_argument(
        "--node-provider",
        "-P",
        help="The node provider",
        choices=["synapse", "libp2p"],
        action="store",
        dest="provider",
    )
    parser.add_argument(
        "--proxy-dump-payloads",
        help="Debug option to make the CoAP proxy log the packets that are being sent/received",
        action="store_true",
    )
    args = parser.parse_args()
    app.config['ARGS'] = args

    host = args.host
    os.environ["POSTGRES_HOST"] = host
    os.environ["SYNAPSE_LOG_HOST"] = host

    if args.jaeger:
        os.environ["SYNAPSE_JAEGER_HOST"] = host

    if args.use_proxy:
        os.environ["SYNAPSE_USE_PROXY"] = "1"

    if args.proxy_dump_payloads:
        os.environ["PROXY_DUMP_PAYLOADS"] = "1"

    provider = None
    if args.provider == "synapse":
        from meshsim.ext.synapse import SynapseProvider
        provider = SynapseProvider()
    elif args.provider == "libp2p":
        from meshsim.ext.libp2p import Libp2pProvider
        provider = Libp2pProvider()
    else:
        raise ValueError(
            "Provider not defined or missing ({})".format(args.provider))

    # Not ideal but better than pure globals
    app.node_provider = provider
    app.mesh = Mesh(provider)

    provider.init_client_health_host()

    app.run(host="0.0.0.0", port=args.port, debug=True)


if __name__ == "__main__":
    main()
