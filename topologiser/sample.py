#!/usr/bin/env python3

from provider.ext.libp2p.p2pd_wrapper import P2PDWrapper

wrapper1 = P2PDWrapper()
print(wrapper1.identify())
