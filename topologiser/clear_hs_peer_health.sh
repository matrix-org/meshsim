#!/bin/bash -x

NUM_FLOWS=$1

GW=`cat /tmp/gw`

tc qdisc del dev eth0 root

# we have to set an explicit priomap when bands != 3
# this PRIO is just used to define children for the root, not for prioritising traffic.
tc qdisc add dev eth0 root handle 1: prio bands $NUM_FLOWS priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0

# set the default queue for talking to the host
tc qdisc add dev eth0 parent 1:1 handle 10: sfq

# filter default traffic to that queue.
tc filter add dev eth0 protocol ip parent 1: \
    u32 match ip dst $GW \
    flowid 1:1
