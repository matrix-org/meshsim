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
  echo 'Usage: ./start_hs.sh <HS_ID> <DOCKER_HOST_IP>'
  exit 1
fi

set -x

HSID=$1
HOST_IP=$2

# Postgres runs in the same network, using this preset name
POSTGRES_CONTAINER_NAME=pg-mesh
POSTGRES_IP=$(docker inspect $POSTGRES_CONTAINER_NAME --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')

# for db in account device mediaapi syncapi roomserver serverkey federationsender publicroomsapi appservice naffka; do
#     createdb -O dendrite dendrite${HSID}_$db
# done

# # make sure that you have a monolith image built as:
# # docker build -t monolith .
# # using our custom Dockerfile for dendrite (n.b. *not* docker-compose.yml, as we use a local postgres)

# if [[ ! -z `docker container ls -f name=synapse${HSID} -q -a` ]]
# then
# 	# reuse existing container
# 	exit
# fi

# docker run -d --name dendrite$HSID -e HSID monolith

docker cp ./scripts/synapse_template.sql pg-mesh:/synapse_template.sql

cat <<HERE | docker exec -i pg-mesh /bin/bash -x

stat /synapse_template.sql
export PGUSER=postgres

if ! dropdb --if-exists synapse${HSID} ; then
	echo "Failed to drop database, bailing"
	exit 1
fi

psql --variable="ON_ERROR_STOP=" -f /synapse_template.sql #> /dev/null 2>&1
createdb -O synapse synapse${HSID} -T synapse_template

# shouldn't we put this in the template?
psql synapse$HSID <<EOT
insert into users(name, password_hash) values ('@matthew:synapse$HSID', '\$2b\$12\$oOZr9g6bPScmPrpJHv/uuu2piCg7kN8ia/BAlfW6wske/1kLf8kze');
insert into access_tokens(id, user_id, token) values (123123, '@matthew:synapse$HSID', 'fake_token');
insert into profiles(user_id) values ('matthew');
EOT

HERE

# insert into users(name, password_hash) values ('@amandine:synapse$HSID', '\$2b\$12\$oOZr9g6bPScmPrpJHv/uuu2piCg7kN8ia/BAlfW6wske/1kLf8kze');
# insert into access_tokens(id, user_id, token) values (123123, '@amandine:synapse$HSID', 'fake_token');
# insert into profiles(user_id) values ('amandine');

# build our synapse via:
# docker build -t synapse -f docker/Dockerfile .

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

docker run -d --name synapse$HSID \
	--privileged \
	--network mesh \
	--hostname synapse$HSID \
	-e SYNAPSE_SERVER_NAME=synapse${HSID} \
	-e SYNAPSE_REPORT_STATS=no \
	-e SYNAPSE_ENABLE_REGISTRATION=yes \
	-e SYNAPSE_LOG_LEVEL=INFO \
	-e POSTGRES_DB=synapse$HSID \
	-e POSTGRES_PASSWORD=synapseftw \
	-p $((18000 + HSID)):8008 \
	-p $((19000 + HSID)):3000 \
	-p $((20000 + HSID)):5683/udp \
	-e POSTGRES_HOST=$POSTGRES_IP \
	-e SYNAPSE_LOG_HOST=$HOST_IP \
	-e SYNAPSE_USE_PROXY=1 \
	-e PROXY_DUMP_PAYLOADS=1 \
	synapse

# or replace the last line for a dummy docker...
# 	--entrypoint '' \
#	synapse \
#	sleep 365d

# One can also mount an actual synapse working directory to be able to quickly
# edit synaspe without rebuilding. Simply requires a docker restart after edit...
# --mount type=bind,source=/home/erikj/git/synapse/synapse,destination=/usr/local/lib/python3.7/site-packages/synapse \
# Similiarly for the coap-proxy:
# --mount type=bind,source=/home/erikj/git/coap-proxy,destination=/proxy

# to inspect:
# docker run -i -t --entrypoint /bin/bash synapse
