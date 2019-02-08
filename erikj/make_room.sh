#!/bin/bash

curl -XPOST "http://localhost:18000/_matrix/client/r0/createRoom?access_token=fake_token" -d '{"preset":"public_chat", "room_alias_name": "test"}'
