#!/bin/bash

ids=`docker container ls -f name=meshsim-node -q -a`

if [[ ! -z $ids ]]
then
	echo "stopping $ids"
	docker stop -t 0 $ids
	docker rm $ids
fi