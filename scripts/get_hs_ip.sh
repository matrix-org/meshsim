#!/bin/bash

HSID=$1

docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' synapse$HSID
