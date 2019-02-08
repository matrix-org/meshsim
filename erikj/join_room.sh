#!/bin/bash

END=$1

function join {
        port=$1
        res=$(curl "http://localhost:$port/_matrix/client/r0/join/%23test:synapse0?access_token=fake_token" -XPOST -s)
        echo "Result from $port: $res"
}

for i in $(seq 0 $END); do
        port=$(expr 18000 + $i)
        join $port
        # sleep 2
done

wait
