# Meshsim Node (topologiser)

The agent that runs on each mesh node and controls peering, networking and additional functionality.

Handles two flavors of nodes:
- synapse (matrix.org) instances
- p2pd (https://github.com/libp2p/go-libp2p-daemon) instances

## synapse

##### Network
The mesh connections are controlled by altering the routing table (`ip route`) and qdiscs (`tc qdisc`) within each container.

##### Message sending
Topologiser talks to synapse via it's local [http api](https://matrix.org/docs/spec/r0.0.0/client_server).

## p2pd: the libp2p daemon

Topologiser talks to p2pd via IPC (unix socket), according to the protobuf
[specification](https://github.com/libp2p/go-libp2p-daemon/tree/master/specs).

##### Network
Peer connect/disconnect is handled via p2pd's IPC:
	https://github.com/libp2p/go-libp2p-daemon/blob/master/specs/CONTROL.md#connect

##### Message sending
Messaging is controlled by topologiser via the PUBSUB IPC:
	https://github.com/libp2p/go-libp2p-daemon/blob/master/specs/PUBSUB.md

