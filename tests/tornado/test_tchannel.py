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

from __future__ import absolute_import

import pytest
import os

from tchannel.errors import AlreadyListeningError
from tchannel.tornado import TChannel
from tchannel.tornado.peer import Peer


@pytest.fixture
def tchannel():
    return TChannel(name='test')


@pytest.fixture
def peer(tchannel):
    return Peer(tchannel, "localhost:4040")


@pytest.mark.gen_test
def test_peer_caching(tchannel, peer):
    "Connections are long-lived and should not be recreated."""
    tchannel.peers.add(peer)
    assert tchannel.peers.get("localhost:4040") is peer


def test_known_peers():
    peers = ["localhost:%d" % port for port in range(4040, 4101)]
    tchannel = TChannel('test', known_peers=peers)

    for peer in peers:
        assert tchannel.peers.lookup(peer)


def test_is_listening_should_return_false_when_listen_not_called(tchannel):

    assert tchannel.is_listening() is False


def test_is_listening_should_return_true_when_listen_called(tchannel):

    tchannel.listen()

    assert tchannel.is_listening() is True


def test_should_error_if_call_listen_twice(tchannel):

    tchannel.listen()

    with pytest.raises(AlreadyListeningError):
        tchannel.listen()


def test_advertise_should_listen_if_not_called_yet(tchannel, mock_server):

    assert tchannel.is_listening() is False

    mock_server.expect_call('ad', 'json').and_write(
        headers="",
        body={"hello": "world"},
    )

    routers = [mock_server.tchannel.hostport]

    tchannel.advertise(
        routers=routers
    )

    assert tchannel.is_listening() is True


def test_advertise_should_take_a_router_file(tchannel, mock_server):

    mock_server.expect_call('ad', 'json').and_write(
        headers="",
        body={"hello": "world"},
    )

    host_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../data/hosts.json',
    )

    tchannel.advertise(
        routers=None,
        router_file=host_path
    )

    assert tchannel.is_listening() is True
