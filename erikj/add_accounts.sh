#!/bin/bash

END=$1

# the default password is 'secret'
password_hash='$2b$12$sN0ba4CTkf0Z5n2OVdGekuEt1cJreZljx2AYFZQCBNhAMwpSXhIwK'

for i in $(seq 0 $END); do
        psql -h localhost -p 6645 synapse$i <<<"insert into access_tokens(id, user_id, token) values (123123, '@matthew:synapse$i', 'fake_token');";
done
