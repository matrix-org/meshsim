#!/bin/bash -x

HSID=$1

#docker stop dendrite$HSID

docker stop -t 0 meshsim-node$HSID
docker rm meshsim-node$HSID