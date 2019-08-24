#!/bin/bash

if [[ `uname` != Darwin ]]
then
	exit
fi

# inspired by https://gist.github.com/dreness/20d7ae82df3997be5d47

# needs in sudoers:
#
# matthew         ALL = (root) NOPASSWD: /usr/sbin/dnctl
# matthew         ALL = (root) NOPASSWD: /sbin/pfctl

# Reset dummynet to default config
sudo dnctl -f flush

# Compose an addendum to the default config to create a new anchor and table file
read -d '' -r PF <<EOF
dummynet-anchor "myanchor"
anchor "myanchor"
EOF

# Reset PF to default config and apply our addendum
(cat /etc/pf.conf && echo "$PF") | sudo pfctl -q -f -

# Configure the new anchor
cat <<EOF | sudo pfctl -q -a myanchor -f -
dummynet out on lo0 proto tcp from any to 127.0.0.1 port 18000:18200 pipe 1
dummynet out on lo0 proto udp from any to 127.0.0.1 port 20000:20200 pipe 1
EOF

# Create the dummynet queue
sudo dnctl pipe 1 config

# Show new configs
# printf "\nGlobal pf dummynet anchors:\n"
# sudo pfctl -q -s dummynet
# printf "\nmyanchor config:\n"
# sudo pfctl -q -s dummynet -a myanchor
# printf "\ndummynet config:\n"
# sudo dnctl show queue

# Enable PF
sudo pfctl -E