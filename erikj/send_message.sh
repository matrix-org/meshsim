#!/bin/bash

END=$1
MESSAGE=$2

function send_message {
        id=$1
        port=$(expr 18000 + $id)
        room_id=$2
        res=$(curl "http://localhost:$port/_matrix/client/r0/rooms/$room_id/send/m.room.message?access_token=fake_token" -XPOST -s -d'{"body":"test from '$port': '"$MESSAGE"'", "msgtype":"m.text"}')
        echo "Result from $id: $res" 
}

res=$(curl "http://localhost:18000/_matrix/client/r0/join/%23test:synapse0?access_token=fake_token" -XPOST -s)
res=$(echo $res | tr '\n' ' ')
room_id=$(echo $res | jq -r '.room_id')

for i in $(seq 0 $END); do
        send_message $i $room_id
#        sleep 2
done

wait
