#!/bin/bash -x

HSID=$1

# for db in account device mediaapi syncapi roomserver serverkey federationsender publicroomsapi appservice naffka; do
#     dropdb dendrite${HSID}_$db
# done

# docker rm dendrite$HSID

dropdb synapse${HSID}
docker rm meshsim-node$HSID