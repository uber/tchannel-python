# encoding=utf8

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

import mock
import pytest
from tornado import gen

from tchannel import TChannel
from tchannel.errors import NoAvailablePeerError

from tchannel.tornado import peer as tpeer
from tchannel.tornado.stream import InMemStream
from tchannel.tornado.stream import read_full


def closed_stream(body):
    """Builds an in-memory stream whose entire request body is the given string.

    :param body:
        Request body for the returned Stream
    """
    stream = InMemStream(body)
    stream.close()
    return stream


def mocked_stream():
    # An object that conforms to the stream interface but isn't an instance of
    # Stream.
    def reader():
        if stream.read.call_count == 3:
            return gen.maybe_future('')
        else:
            return gen.maybe_future('foo')

    stream = mock.Mock()
    stream.read.side_effect = reader

    return stream


def test_basic_peer_management_operations():
    peer_group = tpeer.PeerGroup(mock.MagicMock())

    assert not peer_group.hosts
    assert not peer_group.peers
    assert not peer_group.lookup('localhost:4040')

    p = peer_group.get('localhost:4040')

    assert p
    assert peer_group.lookup('localhost:4040') is p
    assert peer_group.get('localhost:4040') is p

    assert peer_group.remove('localhost:4040') is p
    assert not peer_group.lookup('localhost:4040')

    peer_group.add(p)
    assert peer_group.hosts == ['localhost:4040']
    assert peer_group.peers == [p]


@pytest.mark.parametrize('s, expected', [
    (None, b''),
    ('foo', b'foo'),
    (u'☃', b'\xe2\x98\x83'),
    (bytearray([0x12, 0x34]), b'\x12\x34'),
    (closed_stream('foo'), b'foo'),
    (mocked_stream(), b'foofoo')
])
@pytest.mark.gen_test
def test_maybe_stream(s, expected):
    got = yield read_full(tpeer.maybe_stream(s))
    assert expected == got


@pytest.mark.gen_test
def test_peer_connection_failure():
    # Test connecting a peer when the first connection attempt fails.

    MockConnection = mock.MagicMock()
    connection = mock.MagicMock()

    called = [False]

    with mock.patch.object(tpeer.Peer, 'connection_class', MockConnection):

        @gen.coroutine
        def try_connect(*args, **kwargs):
            if not called[0]:
                # If this is the first call, fail.
                called[0] = True
                raise ZeroDivisionError('great sadness')
            else:
                raise gen.Return(connection)

        MockConnection.outgoing.side_effect = try_connect

        peer = tpeer.Peer(mock.MagicMock(), 'localhost:4040')

        future = peer.connect()
        with pytest.raises(ZeroDivisionError) as excinfo:
            yield future

        assert 'great sadness' in str(excinfo)

        got = yield peer.connect()
        assert got is connection

        assert MockConnection.outgoing.call_count == 2


@pytest.mark.gen_test
def test_peer_connection_network_failure():
    # Network errors in connecting to a peer must be retried with a different
    # peer.

    healthy = TChannel('healthy-server')
    healthy.listen()

    unhealthy = TChannel('unhealthy-server')
    unhealthy.listen()

    # register the endpoint on the healthy host only to ensure that the
    # request wasn't made to the unhealthy one.
    @healthy.raw.register('hello')
    def endpoint(request):
        return 'world'

    known_peers = [healthy.hostport, unhealthy.hostport]
    client = TChannel('client', known_peers=known_peers)

    with mock.patch.object(tpeer.PeerGroup, 'choose') as mock_choose:

        def fake_choose(*args, **kwargs):
            if mock_choose.call_count == 1:
                # First choose the unhealthy host.
                hostport = unhealthy.hostport
            else:
                hostport = healthy.hostport
            # TODO need access to peers in new TChannel
            return client._dep_tchannel.peers.get(hostport)

        mock_choose.side_effect = fake_choose

        # TODO New TChannel doesn't have close() and old one doesn't call
        # stop() on server.
        unhealthy._dep_tchannel._server.stop()

        resp = yield client.raw('server', 'hello', 'foo')
        assert resp.body == 'world'


@pytest.mark.gen_test
def test_peer_connection_failure_exhausted_peers():
    # If we run out of healthy peers while trying to connect, raise
    # NoAvailablePeerError.

    servers = [TChannel('server-%d' % n) for n in xrange(10)]
    for server in servers:
        server.listen()

    known_peers = [server.hostport for server in servers]
    client = TChannel('client', known_peers=known_peers)

    for server in servers:
        # TODO New TChannel doesn't have close() and old one doesn't call
        # stop() on server.
        server._dep_tchannel._server.stop()

    with pytest.raises(NoAvailablePeerError):
        yield client.raw('server', 'hello', 'foo')


@pytest.mark.gen_test
def test_peer_incoming_connections_are_preferred(request):
    incoming = mock.MagicMock()
    outgoing = mock.MagicMock()

    peer = tpeer.Peer(mock.MagicMock(), 'localhost:4040')
    with mock.patch(
        'tchannel.tornado.connection.StreamConnection.outgoing'
    ) as mock_outgoing:
        mock_outgoing.return_value = gen.maybe_future(outgoing)
        peer.connect()

    assert (yield peer.connect()) is outgoing

    peer.register_incoming(incoming)
    assert (yield peer.connect()) is incoming
