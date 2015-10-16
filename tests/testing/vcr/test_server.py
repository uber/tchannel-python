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

from contextlib2 import contextmanager

# from tchannel.thrift import client_for
from tchannel.errors import TChannelError
from tchannel import TChannel
from tchannel.tornado.stream import InMemStream
from tchannel.testing.vcr import proxy
from tchannel.testing.vcr.server import VCRProxyService


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
def unpatch():
    @contextmanager
    def reset():
        yield
    return reset


@pytest.yield_fixture
def vcr_service(cassette, unpatch, io_loop):
    with VCRProxyService(cassette, unpatch) as vcr_service:
        yield vcr_service


@pytest.fixture
def vcr_hostport(vcr_service):
    return vcr_service.hostport


@pytest.fixture(params=[True, False], ids=['hostPort', 'knownPeers'])
def use_known_peers(request):
    return request.param


@pytest.fixture
def call(mock_server, use_known_peers, vcr_hostport):
    """A fixture that returns a function to send a call through the system."""

    tchannel = TChannel('proxy-client')

    def f(endpoint, body, headers=None, service=None):
        kwargs = {
            'serviceName': service or '',
            'endpoint': endpoint,
            'headers': headers or '',
            'body': body,
        }
        if use_known_peers:
            kwargs['knownPeers'] = [mock_server.hostport]
        else:
            kwargs['hostPort'] = mock_server.hostport
        vcr_request = proxy.Request(**kwargs)
        return tchannel.thrift(
            proxy.VCRProxy.send(vcr_request),
            hostport=vcr_hostport,
        )

    return f


@pytest.mark.gen_test
def test_replay(cassette, call):
    allow(cassette).can_replay.and_return(True)
    expect(cassette).replay.and_return(
        proxy.Response(
            code=0, headers='{key: value}', body='response body'
        )
    )

    response = yield call('endpoint', 'request body')
    assert response.body.code == 0
    assert response.body.body == 'response body'
    assert response.body.headers == '{key: value}'


@pytest.mark.gen_test
def test_record(vcr_service, cassette, call, mock_server, use_known_peers):
    allow(cassette).can_replay.and_return(False)
    expect(cassette).record.with_args(
        proxy.Request(
            serviceName='service',
            endpoint='endpoint',
            headers='headers',
            body='body',
            knownPeers=[mock_server.hostport] if use_known_peers else [],
            hostPort='' if use_known_peers else mock_server.hostport,
        ),
        proxy.Response(
            code=0,
            headers='response headers',
            body='response body',
        ),
    )

    mock_server.expect_call('endpoint').and_write(
        headers='response headers',
        body='response body',
    ).once()

    response = yield call(
        service='service',
        endpoint='endpoint',
        headers='headers',
        body='body',
    )

    assert response.body.headers == 'response headers'
    assert response.body.body == 'response body'


@pytest.mark.gen_test
def test_write_protected(vcr_service, cassette, call):
    cassette.record_mode = 'none'
    cassette.write_protected = True
    allow(cassette).can_replay.and_return(False)

    with pytest.raises(proxy.CannotRecordInteractionsError):
        yield call('endpoint', 'request body')


@pytest.mark.gen_test
def test_no_peers(vcr_service, cassette, vcr_hostport):
    allow(cassette).can_replay.and_return(False)
    vcr_request = proxy.Request(
        serviceName='hello_service',
        endpoint='hello',
        headers='',
        body='body',
    )
    with pytest.raises(proxy.NoPeersAvailableError):
        yield TChannel('foo').thrift(
            proxy.VCRProxy.send(vcr_request),
            hostport=vcr_hostport,
        )


@pytest.mark.gen_test
def test_unexpected_error(vcr_service, cassette, call):
    allow(cassette).can_replay.and_raise(SomeException("great sadness"))

    with pytest.raises(proxy.VCRServiceError) as exc_info:
        yield call('endpoint', 'body')

    assert 'great sadness' in str(exc_info)


@pytest.mark.gen_test
def test_protocol_error(vcr_service, cassette, call, mock_server):
    allow(cassette).can_replay.and_return(False)
    expect(cassette).record.never()

    mock_server.expect_call('endpoint').and_raise(
        TChannelError.from_code(1, description='great sadness')
    )

    with pytest.raises(proxy.RemoteServiceError) as exc_info:
        yield call('endpoint', 'body')

    assert 'great sadness' in str(exc_info)
    assert exc_info.value.code == 1


class SomeException(Exception):
    pass
