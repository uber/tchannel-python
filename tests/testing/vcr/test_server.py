from __future__ import absolute_import

import pytest
from doubles import InstanceDouble, allow, expect

from tornado import gen

import tchannel.testing.vcr.types as vcr
from tchannel.tornado import TChannel
from tchannel.tornado.stream import InMemStream
from tchannel.tornado.response import Response
from tchannel.testing.vcr.server import FakeServer


def stream(s):
    s = InMemStream(s)
    s.close()
    return s


@pytest.fixture
def cassette():
    return InstanceDouble('tchannel.testing.vcr.cassette.Cassette')


@pytest.fixture
def real_peer():
    peer = InstanceDouble('tchannel.tornado.peer.Peer')
    peer.hostport = 'localhost:40000'
    return peer


@pytest.yield_fixture
def server(cassette, real_peer, io_loop):
    with FakeServer(cassette, real_peer) as server:
        yield server


@pytest.fixture
def call(server):
    channel = TChannel('test-client')

    def f(endpoint, body, headers=None, service=None, scheme=None):
        return channel.request(
            hostport=server.hostport,
            service=service,
            arg_scheme=scheme,
        ).send(endpoint, headers or '', body)

    return f


@pytest.mark.gen_test
def test_can_replay(server, cassette, call):
    allow(cassette).can_replay.and_return(True)
    expect(cassette).replay.and_return(
        vcr.Response(0, '{key: value}', 'response body')
    )

    response = yield call('endpoint', 'request body')
    assert response.status_code == 0
    assert (yield response.get_header()) == '{key: value}'
    assert (yield response.get_body()) == 'response body'


@pytest.mark.gen_test
def test_cant_replay(server, cassette, real_peer, call):
    allow(cassette).can_replay.and_return(False)
    expect(cassette).record.with_args(
        vcr.Request('service', 'endpoint', 'headers', 'body'),
        vcr.Response(0, 'response headers', 'response body'),
    )

    response = Response(
        argstreams=[
            stream('endpoint'),
            stream('response headers'),
            stream('response body'),
        ]
    )

    clientop = InstanceDouble('tchannel.tornado.peer.PeerClientOperation')
    expect(clientop).send.and_return(gen.maybe_future(response))
    allow(real_peer).request.and_return(clientop)

    response = yield call(
        service='service',
        endpoint='endpoint',
        headers='headers',
        body='body',
    )

    assert (yield response.get_header()) == 'response headers'
    assert (yield response.get_body()) == 'response body'
