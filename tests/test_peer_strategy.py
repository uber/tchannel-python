# Copyright (c) 2016 Uber Technologies, Inc.
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

from __future__ import absolute_import

import sys

import pytest
from tchannel import TChannel
from tchannel.peer_strategy import PreferIncomingCalculator
from tchannel.tornado.connection import TornadoConnection
from tchannel.tornado.connection import INCOMING
from tchannel.tornado.peer import Peer


@pytest.mark.gen_test
def test_get_rank_no_connection():
    server = TChannel('server')
    server.listen()
    peer = Peer(TChannel('test'), '10.10.101.21:230')
    calculator = PreferIncomingCalculator()
    assert sys.maxint == calculator.get_rank(peer)


@pytest.mark.gen_test
def test_get_rank_with_outgoing():
    server = TChannel('server')
    server.listen()
    connection = yield TornadoConnection.outgoing(server.hostport)

    peer = Peer(TChannel('test'), '10.10.101.21:230')
    calculator = PreferIncomingCalculator()
    peer.register_outgoing_conn(connection)
    assert PreferIncomingCalculator.TIERS[1] == calculator.get_rank(peer)


@pytest.mark.gen_test
def test_get_rank_with_imcoming():
    server = TChannel('server')
    server.listen()
    connection = yield TornadoConnection.outgoing(server.hostport)
    connection.direction = INCOMING
    peer = Peer(TChannel('test'), '10.10.101.21:230')
    calculator = PreferIncomingCalculator()
    peer.register_incoming_conn(connection)
    assert sys.maxint != calculator.get_rank(peer)


@pytest.mark.gen_test
def test_get_rank_ephemeral():
    server = TChannel('server')
    server.listen()
    connection = yield TornadoConnection.outgoing(server.hostport)
    connection.direction = INCOMING
    peer = Peer(TChannel('test'), '10.10.101.21:230')
    peer.register_incoming_conn(connection)

    peer.host = '0.0.0.0'
    peer.port = 0
    calculator = PreferIncomingCalculator()
    assert sys.maxint == calculator.get_rank(peer)
