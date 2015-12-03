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
import tornado.ioloop
import tornado.testing

from tchannel.messages import Types
from tchannel import TChannel
from tchannel.tornado.connection import StreamConnection
from tchannel.tornado.message_factory import MessageFactory


def dummy_headers():
    return {
        'host_port': 'fake:1234',
        'process_name': 'honeybooboo',
    }


class ConnectionTestCase(tornado.testing.AsyncTestCase):
    @pytest.fixture(autouse=True)
    def make_server_client(self, tornado_pair):
        self.server, self.client = tornado_pair

    @tornado.testing.gen_test
    def test_handshake(self):
        """Verify we handshake in an async manner."""
        headers = dummy_headers()

        self.client.initiate_handshake(headers=headers)
        yield self.server.expect_handshake(headers=headers)

        assert self.client.requested_version == self.server.requested_version

    @tornado.testing.gen_test
    def test_pings(self):
        """Verify calls are sent to handler properly."""
        self.client.ping()

        ping = yield self.server.await()
        assert ping.message_type == Types.PING_REQ

        self.server.pong()

        pong = yield self.client.await()
        assert pong.message_type == Types.PING_RES


@pytest.mark.gen_test
def test_close_callback_is_called():
    server = TChannel('server')
    server.listen()

    cb_future = tornado.gen.Future()

    conn = yield StreamConnection.outgoing(
        server.hostport, tchannel=mock.MagicMock()
    )
    conn.set_close_callback(lambda: cb_future.set_result(True))

    conn.close()

    assert (yield cb_future)


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
