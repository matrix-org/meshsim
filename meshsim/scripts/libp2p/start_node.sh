#!/bin/bash

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

if [ "$#" -ne 2 ]
then
  echo 'Usage: ./start_node.sh <HS_ID> <DOCKER_HOST_IP>'
  exit 1
fi
set -x

# build our libp2p-daemon via:
# docker build -t libp2p-daemon -f libp2p-daemon/Dockerfile.meshsim .

# ensure our network exists with:
# docker network create --driver bridge mesh

# ensure that KSM is enabled on the host:
#
# for macOS:
# screen ~/Library/Containers/com.docker.docker/Data/vms/0/tty
# echo 1 > /sys/kernel/mm/ksm/run
# echo 10000 > /sys/kernel/mm/ksm/pages_to_scan # 40MB of pages at a time
# grep -H '' /sys/kernel/mm/ksm/run/*
#
# N.B. if (and only if) we're playing around with MTU, will need something like:
# ip link set dev br-757a634a355d mtu 150
# ...or whatever our bridge is, as PMTU doesn't seem to be working
# and otherwise we'll get locked out of the guest.

docker run -d --name meshsim-node$HSID \
	--privileged \
	--network mesh \
	--hostname meshsim-node$HSID \
	-p $((19000 + HSID)):3000 \
	-e PROXY_DUMP_PAYLOADS=1 \
	-e LOG_HOST=$HOST_IP \
	-e NODE_HOST=meshsim-node$HSID \
	-e TOPOLOGISER_MODE=libp2p \
	p2pd-meshsim
