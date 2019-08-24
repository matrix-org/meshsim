#!/bin/bash -x

SRCPORT=$1
BW=$2
DELAY=$3
JITTER=$4

# n.b. srcport & jitter not supported yet

# On Docker-for-mac we can't do ingress traffic shaping in the linux containers
# as the linux host VM has no IFB module and we don't want to waste our lives
# compiling it.
#
# So instead we shape the traffic on the ingress.

if [[ `uname` != Darwin ]]
then
	exit
fi

sudo dnctl pipe 1 config bw ${BW}bits/s delay $DELAY