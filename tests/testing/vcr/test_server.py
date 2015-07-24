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
from doubles import InstanceDouble, allow, expect

from tornado import gen

import tchannel.testing.vcr.types as vcr
from tchannel.tornado import TChannel
from tchannel.tornado.stream import InMemStream
from tchannel.tornado.response import Response
from tchannel.testing.vcr.server import FakeServer
from tchannel.testing.vcr.exceptions import CannotWriteCassetteError


def stream(s):
    s = InMemStream(s)
    s.close()
    return s


@pytest.fixture
def cassette():
    cass = InstanceDouble('tchannel.testing.vcr.cassette.Cassette')
    cass.write_protected = False
    return cass


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
def test_replay(server, cassette, call):
    allow(cassette).can_replay.and_return(True)
    expect(cassette).replay.and_return(
        vcr.Response(0, '{key: value}', 'response body')
    )

    response = yield call('endpoint', 'request body')
    assert response.status_code == 0
    assert (yield response.get_header()) == '{key: value}'
    assert (yield response.get_body()) == 'response body'


@pytest.mark.gen_test
def test_record(server, cassette, real_peer, call):
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


@pytest.mark.xfail(reason='Pending deletion of FakeServer')
@pytest.mark.gen_test
def test_write_protected(server, cassette, call):
    cassette.write_protected = True
    allow(cassette).can_replay.and_return(False)

    with pytest.raises(CannotWriteCassetteError):
        yield call('endpoint', 'request body')
