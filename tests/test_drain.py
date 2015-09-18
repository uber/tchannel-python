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
import tornado
from tornado.concurrent import Future
from tornado.iostream import StreamClosedError

from tchannel import TChannel
from tchannel import schemes
from tchannel.errors import DeclinedError
from tchannel.errors import NetworkError


@pytest.mark.gen_test
def test_stop():
    server = TChannel("server")

    @tornado.gen.coroutine
    def endpoint(request):
        raise tornado.gen.Return("hello")

    server.raw.register("endpoint")(endpoint)
    server.listen()
    server.stop()

    client = TChannel("client")
    with pytest.raises(NetworkError):
        yield client.call(
            scheme=schemes.RAW,
            service='server',
            arg1='endpoint',
            arg2='req headers',
            arg3='req body',
            hostport=server.hostport,
        )

    server.listen()
    resp = yield client.call(
        scheme=schemes.RAW,
        service='server',
        arg1='endpoint',
        arg2='req headers',
        arg3='req body',
        hostport=server.hostport,
    )
    assert resp.body == "hello"


@pytest.mark.gen_test
def test_drain_no_new_connection():
    server = TChannel("server")
    server.listen()
    server.drain()

    client = TChannel("client")
    with pytest.raises(StreamClosedError):
        yield client.call(
            scheme=schemes.RAW,
            service='server',
            arg1='endpoint',
            arg2='req headers',
            arg3='req body',
            hostport=server.hostport,
        )


def exempt_sample(service_name):
    return True


@pytest.mark.gen_test
def test_drain_state():
    peer1 = TChannel("peer1")
    peer1.listen()

    server = TChannel("server", known_peers=[peer1.hostport])
    server.listen()
    yield server._dep_tchannel.peer_group.choose().connect()
    reason = "testing"
    server.drain(reason=reason, exempt=exempt_sample)
    for peer in server._dep_tchannel.peer_group.peers:
        for con in peer.connections:
            assert con._drain
            assert con._drain.exempt == exempt_sample
            assert con._drain.reason == reason


@pytest.mark.gen_test
def test_drain_waiting_for_inprogress_request(io_loop):
    server = TChannel("server")
    f = Future()

    @tornado.gen.coroutine
    def endpoint(request):
        yield f
        raise tornado.gen.Return("hello")

    server.raw.register("endpoint")(endpoint)
    server.listen()

    client = TChannel("client")

    @tornado.gen.coroutine
    def drain():
        yield server.drain()

    # start draining in the mid of request
    io_loop.call_later(0.1, lambda: drain())
    # trigger the finish of the request after draining
    io_loop.call_later(0.2, lambda: f.set_result(None))

    resp = yield client.call(
        scheme=schemes.RAW,
        service='server',
        arg1='endpoint',
        arg2='req headers',
        arg3='req body',
        hostport=server.hostport,
    )
    assert resp.body == "hello"


@pytest.mark.gen_test
def test_drain_blocking_new_request(io_loop):
    server = TChannel("server")
    f = Future()

    @tornado.gen.coroutine
    def endpoint(request):
        yield f
        raise tornado.gen.Return("hello")

    server.raw.register("endpoint")(endpoint)
    server.listen()

    client = TChannel("client")

    @tornado.gen.coroutine
    def drain():
        yield server.drain()

    # start draining in the mid of request
    io_loop.call_later(0.1, lambda: drain())
    # trigger the finish of the request after draining
    io_loop.call_later(0.2, lambda: f.set_result(None))

    yield client.call(
        scheme=schemes.RAW,
        service='server',
        arg1='endpoint',
        arg2='req headers',
        arg3='req body',
        hostport=server.hostport,
    )

    with pytest.raises(DeclinedError):
        yield client.call(
            scheme=schemes.RAW,
            service='server',
            arg1='endpoint',
            arg2='req headers',
            arg3='req body',
            hostport=server.hostport,
        )

    for peer in server._dep_tchannel.peer_group.peers:
        for con in peer.connections:
            assert con._drain
            assert len(con.incoming_requests) == 0


@pytest.mark.gen_test
def test_drain_timeout(io_loop):
    server = TChannel("server")
    f = Future()

    @tornado.gen.coroutine
    def endpoint(request):
        yield f
        raise tornado.gen.Return("hello")

    server.raw.register("endpoint")(endpoint)

    server.listen()

    client = TChannel("client")

    @tornado.gen.coroutine
    def drain():
        yield server.drain()

    # start draining in the mid of request
    io_loop.call_later(0.1, lambda: drain())
    # trigger the finish of the request after draining
    io_loop.call_later(0.2, lambda: f.set_result(None))

    yield client.call(
        scheme=schemes.RAW,
        service='server',
        arg1='endpoint',
        arg2='req headers',
        arg3='req body',
        hostport=server.hostport,
    )
