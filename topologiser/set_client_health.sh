#!/bin/bash -x

ID=$1
SRCPORT=$2
BW=$3
DELAY=$4
JITTER=$5

GW=`cat /tmp/gw`


# See set_hs_peer_health.sh for details of all the TC voodoo going on here.

# from https://wiki.linuxfoundation.org/networking/netem

# Ideally we'd do this via IFB, but docker-for-mac's kernel (as of 18.06)
# doesn't have the ifb module, and compiling our own would be a *nightmare*.
# So instead, we shape egresss traffic on both the Mac & Linux side of the bridge.

# modprobe ifb
# ip link set dev ifb0 up
# tc qdisc add dev eth0 ingress
# tc filter add dev eth0 parent ffff: protocol ip u32 match u32 0 0 flowid 1:1 action mirred egress redirect dev ifb0
# tc qdisc add dev ifb0 root netem delay 750ms

BURST=$((`cat /sys/class/net/eth0/mtu` + 14 + 1))

tc qdisc add dev eth0 parent 1:$ID handle ${ID}0: tbf rate ${BW}bit burst $BURST limit 10000
tc qdisc add dev eth0 parent ${ID}0:1 handle ${ID}1: netem delay ${DELAY}ms ${JITTER}ms 25%

tc filter add dev eth0 protocol ip parent 1: \
    u32 match ip dst $GW \
    	match udp src 5683 0xffff \
    flowid 1:$ID

tc filter add dev eth0 protocol ip parent 1: \
    u32 match ip dst $GW \
    	match udp src 8008 0xffff \
    flowid 1:$ID

# fixme; hook up $SRCPORT