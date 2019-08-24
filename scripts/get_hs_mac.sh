#!/bin/bash

HSID=$1

docker inspect -f '{{range .NetworkSettings.Networks}}{{.MacAddress}}{{end}}' synapse$HSID
