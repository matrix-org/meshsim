#!/bin/bash -x

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

PEERID=$1
M0=$2; M1=$3; M2=$4; M3=$5; M4=$6; M5=$7
BW=$8
DELAY=$9
JITTER=${10}

#      root 1: prio
#           /|\
#          / | \
#         /  |  \
#        /   |   \
#      1:1  1:2  1:3
#       |    |    |
#      10:  20:   30:
#      sfq  tbf   tbf
#            |     |
#           20:1  30:1
#            |     |
#           21:   31:
#           delay delay
#            |     |


# our packets look like:
# # tcpdump -i eth0  -vvve -xx -XX -n
# 14:19:49.061214 02:42:ac:12:00:02 > 02:42:ac:12:00:03, ethertype IPv4 (0x0800), length 42: (tos 0x0, ttl 64, id 53241, offset 0, flags [DF], proto ICMP (1), length 28)
#     172.18.0.2 > 172.18.0.3: ICMP echo request, id 179, seq 1, length 8
# 	0x0000:  0242 ac12 0003 0242 ac12 0002 0800 4500  .B.....B......E.
# 	0x0010:  001c cff9 4000 4001 12be ac12 0002 ac12  ....@.@.........
# 	0x0020:  0003 0800 f74b 00b3 0001                 .....K....

# so to filter on destination MAC:

# 	0x0000:  0242 ac12 0003                0800

# sample data:
# M0=02; M1=42; M2=ac; M3=12; M4=00; M5=03
# BW=300
# DELAY=100
# JITTER=10

# burst is the number of bytes that we're allowed to send rapidly before the rate limiting
# kicks in (which then compensates to even things out to hit the target rate).
# it has to be > rate limit/scheduler hz (which is easy, given we're on zero HZ sched).
# it also has to be bigger than MTU, otherwise we'll never gather enough tokens in our bucket to
# be able to send a packet.
#
# limit is the maximum size of packets (in bytes) which we allow to stack up before buffering.
# this is converted to latency (in ms) when viewed by `tc -s disc show`
# e.g. a limit of 3000 bytes == (rate/8 * latency) + burst.
# e.g. (256144/8 * 0.0437) + 1600 = 3000 in the example below:
#
# qdisc tbf 30: dev eth0 parent 1:3 rate 256144bit burst 1599b lat 43.7ms

# we deliberately set the burst rate to be as low as possible - i.e. the MTU (1500 bytes) to smooth
# the bitrate as much as possible. this may overly cripple fast transfers as the token bucket can't
# fill up fast enough but hopefully it'll be okay as our sched is zero hertz.
# It might result in way too many interrupts though.
#
# we deliberately pick MTU + 14 (MAC headers) + 1 to avoid rounding errors
BURST=$((`cat /sys/class/net/eth0/mtu` + 14 + 1))

# N.B. we have to pick a tiny MTU as at a 300bps link, 1514 bytes takes 40s to transfer.
# Ideall we would pick an MTU of 150 (so 14 bytes of MAC, 20 IP, 8 UDP + 106 bytes of payload.)
# otherwise we're going to always get 40s for free where everything works fine before suddenly the
# rate limiting kicks in.  It might be better to just have a better TC module...

tc qdisc add dev eth0 parent 1:$PEERID handle ${PEERID}0: tbf rate ${BW}bit burst $BURST limit 10000
tc qdisc add dev eth0 parent ${PEERID}0:1 handle ${PEERID}1: netem delay ${DELAY}ms ${JITTER}ms 25%

tc filter add dev eth0 protocol ip parent 1: \
    u32 match u16 0x0800 0xFFFF at -2 \
        match u32 0x$M2$M3$M4$M5 0xFFFFFFFF at -12 \
        match u16 0x$M0$M1 0xFFFF at -14 \
    flowid 1:$PEERID

# to diagnose:
#
# tc qdisc show dev eth0
# tc -s qdisc show dev eth0
# tc filter show dev eth0

# or if we were doing it by IP:

#tc filter add dev eth0 protocol ip parent 1:0 prio 3 u32 match ip dst ${PEER}/32 flowid 1:3
