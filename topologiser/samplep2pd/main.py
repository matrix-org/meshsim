#!/usr/bin/env python

import os
import socket
import struct
import p2pd_pb2
import bitcoin.base58

from multiaddr import Multiaddr

from google.protobuf.internal.encoder import _VarintEncoder
from google.protobuf.internal.decoder import _DecodeVarint32

def encode_varint(value):
    """ Encode an int as a protobuf varint """
    data = []
    _VarintEncoder()(data.append, value, False)
    return b''.join(data)

def decode_varint(data):
    """ Decode a protobuf varint to an int """
    return _DecodeVarint(data, 0)[0]

def build_message(data):
    out = req.SerializeToString()
    size = encode_varint(len(out))
    return size + out

SOCKET_FILE = "/tmp/p2pd.sock"

req = p2pd_pb2.Request()
req.type = p2pd_pb2.Request.CONNECT
req.connect.peer = bitcoin.base58.decode("QmPKrbi6x4tRMrXCJj8h2W3XkNZu7XNArMoyJv5WG5YSeg")

req.connect.addrs.extend([
    Multiaddr("/ip4/192.168.122.1/tcp/37245").to_bytes()
])
req.connect.timeout = 100

#x = Multiaddr("/ip4/192.168.122.1/tcp/37539").to_bytes()
#print(bin(int("0x" + x)))

if os.path.exists(SOCKET_FILE):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(SOCKET_FILE)
    client.sendall(build_message(req.SerializeToString()))

    r = client.recv(65000)
    print("GOT")

    resp = p2pd_pb2.Response().ParseFromString(r)
    print(r)
    print("DECODE")
    print(resp)

else:
    print("CANNOT CONNECT, SOCKET NOT FOUND")


