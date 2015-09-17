from __future__ import absolute_import
import pytest
from tchannel import TChannel
from tchannel import schemes
from tchannel.errors import DeclinedError
import tornado
from tornado.concurrent import Future
from tornado.iostream import StreamClosedError


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
            assert con.draining
            assert con.drain_exempt == exempt_sample
            assert con.drain_reason == reason


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
    io_loop.call_later(0.01, lambda: drain())
    # trigger the finish of the request after draining
    io_loop.call_later(0.02, lambda: f.set_result(None))

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
    io_loop.call_later(0.01, lambda: drain())
    # trigger the finish of the request after draining
    io_loop.call_later(0.02, lambda: f.set_result(None))

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
            assert con.draining
            assert len(con.incoming_requests) == 0
