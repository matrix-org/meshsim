import os
import socket
import bitcoin.base58

from .p2pd_pb2 import Request, Response, PSRequest
from multiaddr import Multiaddr
from .p2pd_helpers import recv_message, build_message


SOCKET_FILE = "/tmp/p2pd.sock"


class P2PDWrapper():
    def __init__(self):
        self.client = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM)
        self.client.connect(SOCKET_FILE)

    def connect(self, peer):
        req = Request()
        req.type = Request.CONNECT
        req.connect.peer = bitcoin.base58.decode(peer['id'])
        req.connect.addrs.extend([
            Multiaddr(addr).to_bytes() for addr in peer['addrs']
        ])
        req.connect.timeout = 100
        return self.__send_request(req, Response)

    def disconnect(self, peer):
        req = Request()
        req.type = Request.DISCONNECT
        req.connect.peer = bitcoin.base58.decode(peer['id'])
        return self.__send_request(req, Response)

    def subscribe(self, topic):
        req = Request()
        req.type = Request.PUBSUB
        req.pubsub.type = PSRequest.SUBSCRIBE
        req.pubsub.topic = topic
        return self.__send_request(req, Response)

    def __send_request(self, req, resp_type):
        self.client.sendall(build_message(req.SerializeToString()))
        return recv_message(self.client, resp_type)
