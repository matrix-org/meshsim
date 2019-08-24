#!/bin/bash -x

GW=`cat /tmp/gw`
NETWORK=${GW/%0.1/0.0}

# if experimenting with tiny MTU:
#ip link set dev eth0 mtu 150

ip ro flush all
ip ro add $GW dev eth0

# Postgres is dockerised, running in the same network. Ensure we don't kill connectivity.
ip ro add $POSTGRES_HOST dev eth0

ip ro add blackhole $NETWORK/16
ip ro add default via $GW
