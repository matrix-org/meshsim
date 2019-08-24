#!/bin/bash

HSID=$1

docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' meshsim-node$HSID
