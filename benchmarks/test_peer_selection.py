# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import (
    absolute_import, unicode_literals, print_function, division
)

import mock
import random

from tchannel.tornado.peer import (
    Peer as _Peer,
    PeerGroup as _PeerGroup,
)


NUM_PEERS = 1000


class FakeConnection(object):

    def __init__(self, hostport):
        self.hostport = hostport
        self.closed = False

    @classmethod
    def outgoing(cls, hostport, process_name=None, serve_hostport=None,
                 handler=None, tchannel=None):
        return FakeConnection(hostport)

    def add_done_callback(self, cb):
        return cb(self)

    def exception(self):
        return None

    def result(self):
        return self

    def set_close_callback(self, cb):
        pass


class Peer(_Peer):
    connection_class = FakeConnection


class PeerGroup(_PeerGroup):
    peer_class = Peer


def hostport():
    host = b'.'.join(bytes(random.randint(0, 255)) for i in xrange(4))
    port = random.randint(1000, 30000)
    return b'%s:%d' % (host, port)


def peer(tchannel, hostport):
    return Peer(tchannel, hostport)


def test_choose(benchmark):
    tchannel = mock.MagicMock()
    group = PeerGroup(tchannel)

    # Register 1000 random peers
    for i in xrange(NUM_PEERS):
        peer = group.get(hostport())

    connected_peers = set()

    # Add one outgoing connection to a random peer.
    peer = group.peers[random.randint(0, NUM_PEERS-1)]
    peer.connect()
    connected_peers.add(peer.hostport)

    # Add incoming connections from 50 random peers.
    while len(connected_peers) < 50:
        peer = group.peers[random.randint(0, NUM_PEERS-1)]
        if peer.hostport in connected_peers:
            continue
        peer.register_incoming(FakeConnection(peer.hostport))
        connected_peers.add(peer.hostport)

    benchmark(group.choose)
