#!/bin/bash -x

DST=$1
VIA=$2

ip ro add $VIA dev eth0
ip ro add $DST via $VIA
