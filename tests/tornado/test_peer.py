# encoding=utf8
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

import mock
import pytest

from tornado import gen

from tchannel import TChannel
from tchannel.errors import NoAvailablePeerError
from tchannel.tornado import peer as tpeer
from tchannel.tornado.connection import TornadoConnection
from tchannel.tornado.peer import Peer
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
    incoming.closed = False

    outgoing = mock.MagicMock()
    outgoing.closed = False

    peer = tpeer.Peer(mock.MagicMock(), 'localhost:4040')
    with mock.patch(
        'tchannel.tornado.connection.StreamConnection.outgoing'
    ) as mock_outgoing:
        mock_outgoing.return_value = gen.maybe_future(outgoing)
        peer.connect()

    assert (yield peer.connect()) is outgoing

    peer.register_incoming_conn(incoming)
    assert (yield peer.connect()) is incoming


@pytest.fixture
def peer():
    return Peer(
        tchannel=TChannel('peer'),
        hostport='127.0.0.1:21300',
    )


def test_on_conn_change(peer, connection):
    c = [0]

    def conn_change_db(peer):
        c[0] += 1

    peer.set_on_conn_change_callback(conn_change_db)
    peer.register_incoming_conn(connection)
    assert c[0] == 1

    peer.register_outgoing_conn(connection)
    assert c[0] == 2


@pytest.mark.gen_test
def test_outbound_pending_change():
    server = TChannel('server')
    server.listen()
    connection = yield TornadoConnection.outgoing(server.hostport)
    c = [0]

    def outbound_pending_change_callback():
        c[0] += 1

    connection.set_outbound_pending_change_callback(
        outbound_pending_change_callback
    )

    connection.add_pending_outbound()
    assert c[0] == 1
    connection.add_pending_outbound()
    assert c[0] == 2
    connection.remove_pending_outbound()
    assert c[0] == 3
    connection.remove_pending_outbound()
    assert c[0] == 4


@pytest.mark.gen_test
def test_outbound_pending_change_propagate(peer):
    server = TChannel('server')
    server.listen()
    connection = yield TornadoConnection.outgoing(server.hostport)

    peer.register_incoming_conn(connection)
    b = [0]

    def conn_change_db(peer):
        b[0] += 1

    peer.set_on_conn_change_callback(conn_change_db)

    connection.add_pending_outbound()
    assert b[0] == 1
    connection.add_pending_outbound()
    assert b[0] == 2
    connection.remove_pending_outbound()
    assert b[0] == 3
    connection.remove_pending_outbound()
    assert b[0] == 4


@pytest.fixture
def hostports():
    return ['127.0.0.1:' + str(i) for i in range(1, 101)]


def test_choose(hostports):
    tchannel = TChannel('test')
    peer_group = tchannel._dep_tchannel.peers
    for hp in hostports:
        peer_group.get(hp)

    n = len(hostports)
    for _ in hostports:
        peer_group.choose()
        assert peer_group.peer_heap.size() == n


def test_choose_with_blacklist(hostports):
    tchannel = TChannel('test')
    peer_group = tchannel._dep_tchannel.peers
    for hp in hostports:
        peer_group.get(hp)

    n = len(hostports)
    blacklist = set()
    for _ in hostports:
        peer = peer_group.choose(blacklist=blacklist)
        assert peer not in blacklist
        blacklist.add(peer.hostport)
        assert peer_group.peer_heap.size() == n


def test_choose_with_target_hostport(hostports):
    tchannel = TChannel('test')
    peer_group = tchannel._dep_tchannel.peers
    for hp in hostports:
        peer_group.get(hp)

    target = '1.0.0.1:9000'
    peer = peer_group.choose(hostport=target)
    assert target in peer_group.hosts
    assert target == peer.hostport
    assert peer_group.peer_heap.size() == len(hostports)
    assert len(peer_group.hosts) == len(hostports) + 1


@pytest.mark.gen_test
def test_never_choose_ephemeral():
    server = TChannel('server')
    server.listen()

    @server.json.register('hello')
    def hello(request):
        return 'hi'

    # make a request to set up the connection betweeen the two.
    client = TChannel('client')
    yield client.json('server', 'hello', 'world', hostport=server.hostport)
    assert [client.hostport] == server._dep_tchannel.peers.hosts

    assert (server._dep_tchannel.peers.choose() is None), (
        'choose() MUST NOT select the ephemeral peer even if that is the only'
        'available peer'
    )


@pytest.mark.gen_test
def test_never_choose_incoming():
    server = TChannel('server')
    server.listen()

    client = TChannel('client')
    client.listen()  # client has a non-ephemeral port

    @server.json.register('hello')
    def hello(request):
        return 'hi'

    # make a request to set up a connection
    yield client.json('server', 'hello', 'world', hostport=server.hostport)
    assert [client.hostport] == server._dep_tchannel.peers.hosts

    assert (server._dep_tchannel.peers.choose() is None), (
        'server should not know of any peers at this time'
    )


def test_choose_then_get_peer(hostports):
    tchannel = TChannel('test')
    peer_group = tchannel._dep_tchannel.peers
    for hp in hostports:
        peer_group.get(hp)

    target = '1.0.0.1:9000'

    chosen_peer = peer_group.choose(hostport=target)
    gotten_peer = peer_group.get(hostport=target)
    assert chosen_peer is gotten_peer


def test_get_then_choose_peer(hostports):
    tchannel = TChannel('test')
    peer_group = tchannel._dep_tchannel.peers
    for hp in hostports:
        peer_group.get(hp)

    target = '1.0.0.1:9000'

    gotten_peer = peer_group.get(hostport=target)
    chosen_peer = peer_group.choose(hostport=target)
    assert chosen_peer is gotten_peer


def test_multi_get_and_choose_peer(hostports):
    tchannel = TChannel('test')
    peer_group = tchannel._dep_tchannel.peers
    for hp in hostports:
        peer_group.get(hp)

    target = '1.0.0.1:9000'
    expected_gotten_peer = peer_group.get(hostport=target)
    expected_chosen_peer = peer_group.choose(hostport=target)
    for _ in hostports:
        gotten_peer = peer_group.get(hostport=target)
        chosen_peer = peer_group.choose(hostport=target)
        assert gotten_peer is expected_gotten_peer
        assert gotten_peer is expected_chosen_peer
        assert chosen_peer is expected_gotten_peer
        assert chosen_peer is expected_chosen_peer
