#!/bin/bash

ids=`docker container ls -f name=synapse -q -a`

if [[ ! -z $ids ]]
then
	echo "stopping $ids"
	docker stop -t 0 $ids
	docker rm $ids
fi