#!/bin/bash

END=$1

password_hash='$2b$12$sN0ba4CTkf0Z5n2OVdGekuEt1cJreZljx2AYFZQCBNhAMwpSXhIwK'

for i in $(seq 0 $END); do
        psql synapse$i <<<"insert into access_tokens(id, user_id, token) values (123123, '@matthew:synapse$i', 'fake_token');";
done
