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
import socket
import tornado.ioloop
from tornado import gen
from tornado.iostream import IOStream, StreamClosedError

from tchannel import TChannel
from tchannel import messages
from tchannel.errors import TimeoutError, ReadError
from tchannel.tornado import connection
from tchannel.tornado.message_factory import MessageFactory
from tchannel.tornado.peer import Peer
from tchannel.tornado.request import Request
from tchannel.tornado.response import Response


def dummy_headers():
    return {
        'host_port': 'fake:1234',
        'process_name': 'honeybooboo',
    }


@pytest.mark.gen_test
def test_handshake(tornado_pair):
    """Verify we handshake in an async manner."""
    server, client = tornado_pair
    headers = dummy_headers()

    client.initiate_handshake(headers=headers)
    yield server.expect_handshake(headers=headers)

    assert client.requested_version == server.requested_version


@pytest.mark.gen_test
def test_outgoing_handshake_timeout(tornado_pair):
    server, client = tornado_pair
    headers = dummy_headers()

    future = client.initiate_handshake(headers=headers, timeout=0.2)
    msg = yield server.reader.get()
    assert msg.message_type == messages.Types.INIT_REQ
    # The server never responds

    with pytest.raises(TimeoutError) as exc_info:
        yield future
    assert 'Handshake with ' in str(exc_info)
    assert 'timed out.' in str(exc_info)
    assert 'Did not receive an INIT_RES after 0.2 seconds' in str(exc_info)


@pytest.mark.gen_test
def test_pings(tornado_pair):
    """Verify calls are sent to handler properly."""
    server, client = tornado_pair
    client.ping()

    ping = yield server.await()
    assert ping.message_type == messages.Types.PING_REQ

    server.pong()

    pong = yield client.await()
    assert pong.message_type == messages.Types.PING_RES


@pytest.mark.gen_test
def test_close_callback_is_called():
    server = TChannel('server')
    server.listen()

    cb_future = tornado.gen.Future()

    conn = yield connection.StreamConnection.outgoing(
        server.hostport, tchannel=mock.MagicMock()
    )
    conn.set_close_callback(lambda: cb_future.set_result(True))

    conn.close()

    assert (yield cb_future)


@pytest.mark.gen_test
def test_close_callback_is_called_immediately_if_already_closed():
    server = TChannel('server')
    server.listen()

    cb_future = tornado.gen.Future()

    conn = yield connection.StreamConnection.outgoing(
        server.hostport, tchannel=mock.MagicMock()
    )
    conn.close()

    yield gen.moment

    conn.set_close_callback(lambda: cb_future.set_result(True))

    assert (yield cb_future)


@pytest.mark.gen_test
def test_local_timeout_unconsumed_message():
    """Verify that if the client has a local timeout and the server eventually
    sends the message, the client does not log an "Unconsumed message"
    warning.
    """

    server = TChannel('server')

    @server.raw.register('hello')
    @gen.coroutine
    def hello(request):
        yield gen.sleep(0.07)
        raise gen.Return('eventual response')

    server.listen()

    client = TChannel('client')
    with pytest.raises(TimeoutError):
        yield client.raw(
            'server', 'hello', 'world',
            timeout=0.05, hostport=server.hostport,
            # The server will take 70 milliseconds but we allow at most 50.
        )

    # Wait for the server to send the late response and make sure it doesn't
    # log a warning.
    with mock.patch.object(connection.log, 'warn') as mock_warn:  # :(
        yield gen.sleep(0.03)

    assert mock_warn.call_count == 0


@pytest.mark.gen_test
def test_stream_closed_error_on_read(tornado_pair):
    # Test that we don't log an error for StreamClosedErrors while reading.
    server, client = tornado_pair
    future = server.await()
    client.close()

    with mock.patch.object(connection, 'log') as mock_log:  # :(
        with pytest.raises(StreamClosedError):
            yield future

    assert mock_log.error.call_count == 0
    assert mock_log.info.call_count == 1


@pytest.mark.gen_test
def test_other_error_on_read(tornado_pair):
    # Test that we do log errors for non-StreamClosedError failures while
    # reading.
    server, client = tornado_pair

    future = server.await()
    yield client.connection.write(b'\x00\x02\x00\x00')  # bad payload

    with mock.patch.object(connection, 'log') as mock_log:  # :(
        with pytest.raises(ReadError):
            yield future

    assert mock_log.error.call_count == 1
    assert mock_log.info.call_count == 0


@pytest.mark.gen_test
def test_pending_outgoing():
    server = TChannel('server')
    server.listen()

    @server.raw.register
    def hello(request):
        assert server._dep_tchannel.peers.peers[0].total_outbound_pendings == 1
        return 'hi'

    client = TChannel('client')
    yield client.raw(
        hostport=server.hostport,
        body='work',
        endpoint='hello',
        service='server'
    )

    client_peer = client._dep_tchannel.peers.peers[0]
    server_peer = server._dep_tchannel.peers.peers[0]
    assert client_peer.total_outbound_pendings == 0
    assert server_peer.total_outbound_pendings == 0

    class FakeMessageFactory(MessageFactory):
        def build_raw_message(self, context, args, is_completed=True):
            assert client_peer.total_outbound_pendings == 1
            return super(FakeMessageFactory, self).build_raw_message(
                context, args, is_completed,
            )

    client_conn = client_peer.connections[0]
    client_conn.request_message_factory = FakeMessageFactory(
        client_conn.remote_host,
        client_conn.remote_host_port,
    )
    yield client.raw(
        hostport=server.hostport,
        body='work',
        endpoint='hello',
        service='server'
    )

    assert client_peer.total_outbound_pendings == 0
    assert server_peer.total_outbound_pendings == 0


@pytest.mark.gen_test
def test_client_connection_change_callback():
    server = TChannel('server')
    server.listen()

    @server.raw.register
    def hello(request):
        return 'hi'

    client = TChannel('client')
    count = [0]

    def test_cb(peer):
        count[0] += 1

    client._dep_tchannel.peers.get(
        server.hostport)._on_conn_change_cb = test_cb
    yield client.raw(
        hostport=server.hostport,
        body='work',
        endpoint='hello',
        service='server'
    )

    # 1: connection built, 1: sending request, 1: finish sending request
    assert count[0] == 3


@pytest.mark.gen_test
def test_both_connection_change_callback():
    client = TChannel('client')

    with mock.patch.object(Peer, '_on_conn_change') as mock_conn_change:
        server = TChannel('server')
        server.listen()

        @server.raw.register
        def hello(request):
            return 'hi'

        yield client.raw(
            hostport=server.hostport,
            body='work',
            endpoint='hello',
            service='server'
        )
        assert mock_conn_change.call_count == 6


@pytest.mark.gen_test
def test_writer_write_error():
    server, client = socket.socketpair()
    reader = connection.Reader(IOStream(server))
    writer = connection.Writer(IOStream(client))

    # one successful message first
    yield writer.put(messages.PingRequestMessage())
    ping = yield reader.get()
    assert isinstance(ping, messages.PingRequestMessage)

    writer.io_stream.close()
    with pytest.raises(StreamClosedError):
        yield writer.put(messages.PingResponseMessage())


@pytest.mark.gen_test
def test_reader_read_error():
    server, client = socket.socketpair()
    reader = connection.Reader(IOStream(server))
    writer = connection.Writer(IOStream(client))

    yield writer.put(messages.PingRequestMessage())
    ping = yield reader.get()
    assert isinstance(ping, messages.PingRequestMessage)

    reader.io_stream.close()
    future = reader.get()
    with pytest.raises(StreamClosedError):
        yield future


@pytest.mark.gen_test
def test_writer_serialization_error():
    server = TChannel('server')
    server.listen()

    conn = yield connection.StreamConnection.outgoing(
        server.hostport, tchannel=mock.MagicMock()
    )

    with pytest.raises(AttributeError) as exc_info:
        yield conn.send_request(Request(
            id=conn.writer.next_message_id(),
            service='foo',
            endpoint='bar',
            headers={'cn': None},
        ))

    assert "'NoneType' object has no attribute 'encode'" in str(exc_info)


@pytest.mark.gen_test
def test_writer_multiplexing():
    server = TChannel('server')
    server.listen()

    received = {'chunked': False, 'singleframe': False}

    @server.raw.register('chunked')
    def chunked(request):
        received['chunked'] = True
        return b'chunked'

    @server.raw.register('singleframe')
    def singleframe(request):
        received['singleframe'] = True
        return b'singleframe'

    client = TChannel('client')

    chunked_future = client.raw(
        'server', 'chunked',
        bytes([0x00] * 1024 * 1024),  # 1 MB = 16 frames
        hostport=server.hostport,
        timeout=0.5,
    )

    yield client.raw(
        'server', 'singleframe', b'\x00',  # single frame
        hostport=server.hostport,
    )
    assert received['singleframe']
    assert not received['chunked']

    yield chunked_future
    assert received['chunked']


@pytest.mark.gen_test
def test_loop_failure(tornado_pair):
    server, client = tornado_pair
    headers = dummy_headers()

    # ... yeah
    server.tchannel = mock.MagicMock()
    client.tchannel = mock.MagicMock()

    handshake_future = client.initiate_handshake(headers=headers)
    yield server.expect_handshake(headers=headers)
    yield handshake_future

    assert client._handshake_performed
    assert server._handshake_performed

    # We'll put an invalid message into the reader queue. This should cause one
    # iteration of the loop to fail but the system should continue working
    # afterwards.

    yield server.reader.queue.put(gen.maybe_future(42))  # not a message

    id = client.writer.next_message_id()
    response_future = client.send_request(Request(
        id=id,
        service='server',
        endpoint='bar',
        headers={'cn': 'client'},
    ))

    call_req = yield server.await()
    assert call_req.message_type == messages.Types.CALL_REQ

    response = Response(id=id)
    response.close_argstreams(force=True)

    yield server.post_response(response)
    yield response_future

    assert client._handshake_performed
    assert server._handshake_performed

    client.close()

    # The system needs a little time to recognize that the connections were
    # closed.
    yield gen.sleep(0.15)

    assert client.closed
    assert server.closed


@pytest.mark.gen_test
def test_timeout_not_pending(tornado_pair):
    server, client = tornado_pair
    headers = dummy_headers()

    server.tchannel = mock.MagicMock()
    client.tchannel = mock.MagicMock()

    handshake_future = client.initiate_handshake(headers=headers)
    yield server.expect_handshake(headers=headers)
    yield handshake_future

    # Make a request that times out and ensure that a late response is
    # discarded correctly.

    id = client.writer.next_message_id()
    response_future = client.send_request(Request(
        id=id,
        service='server',
        endpoint='bar',
        headers={'cn': 'client'},
        ttl=0.05,
    ))
    assert id in client._outbound_pending_call

    call_req = yield server.await()
    assert call_req.message_type == messages.Types.CALL_REQ

    yield gen.sleep(0.1)  # make the request time out

    assert id in client._request_tombstones
    assert id not in client._outbound_pending_call

    # late response
    yield server.write(messages.ErrorMessage(
        id=id,
        code=messages.ErrorCode.unexpected,
        description='great sadness',
    ))

    with pytest.raises(TimeoutError):
        yield response_future
