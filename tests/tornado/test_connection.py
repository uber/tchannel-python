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
from tornado import gen

from tchannel import TChannel
from tchannel.errors import TimeoutError
from tchannel.tornado import connection
from tchannel.messages import Types


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

    conn = yield connection.StreamConnection.outgoing(
        server.hostport, tchannel=mock.MagicMock()
    )
    conn.set_close_callback(lambda: cb_future.set_result(True))

    conn.close()

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
