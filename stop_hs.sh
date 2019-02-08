#!/bin/bash -x

HSID=$1

#docker stop dendrite$HSID

docker stop -t 0 synapse$HSID
docker rm synapse$HSID