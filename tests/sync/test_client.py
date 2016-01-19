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
from tchannel import thrift
from tchannel.sync import TChannel
from tchannel.errors import TimeoutError, BadRequestError


@pytest.mark.integration
def test_sync_client_should_get_raw_response(mock_server):

    endpoint = 'health'
    mock_server.expect_call(endpoint).and_write(
        headers="",
        body="OK"
    )

    client = TChannel('test-client')

    future = client.raw(
        service='foo',
        hostport=mock_server.hostport,
        endpoint=endpoint,
    )

    response = future.result()

    assert response.headers == ""
    assert response.body == "OK"


@pytest.mark.integration
def test_sync_client_with_injected_threadloop(mock_server, loop):

    endpoint = 'health'
    mock_server.expect_call(endpoint).and_write(
        headers="",
        body="OK"
    )

    client = TChannel('test-client', threadloop=loop)

    future = client.raw(
        service='foo',
        hostport=mock_server.hostport,
        endpoint=endpoint,
    )

    response = future.result()

    assert response.headers == ""
    assert response.body == "OK"


@pytest.mark.integration
def test_advertise_should_result_in_peer_connections(mock_server):

    body = {"hello": "world"}

    mock_server.expect_call('ad', 'json').and_write(
        headers="",
        body=body,
    )

    routers = [
        mock_server.tchannel.hostport
    ]

    client = TChannel('test-client')
    future = client.advertise(routers)
    result = future.result()

    assert result.body == body
    assert client._dep_tchannel.peers.hosts == routers


def test_failing_advertise_should_raise(mock_server):

    mock_server.expect_call('ad', 'json').and_raise(
        Exception('great sadness')
    )

    routers = [mock_server.tchannel.hostport]
    client = TChannel('test-client')

    with pytest.raises(TimeoutError):
        future = client.advertise(routers, timeout=0.1)
        future.result()


def test_should_discover_ip():

    client = TChannel('test-client')
    hostport = client.hostport

    assert '0.0.0.0:0' != hostport


@pytest.mark.gen_test
def test_sync_register_json():
    sync_client = TChannel('test-client')

    @sync_client.json.register
    def hello(request):
        return {}

    sync_client.listen()

    from tchannel import TChannel as AsyncTchannel
    async_client = AsyncTchannel('s')
    with pytest.raises(BadRequestError):
        yield async_client.json(
            service='test-client',
            endpoint='hello',
            hostport=sync_client.hostport
        )

    sync_client.json.register(hello)
    with pytest.raises(BadRequestError):
        yield async_client.json(
            service='test-client',
            endpoint='hello',
            hostport=sync_client.hostport
        )


@pytest.mark.gen_test
def test_sync_register_raw():
    sync_client = TChannel('test-client')

    @sync_client.json.register
    def hello(request):
        return ""

    sync_client.listen()

    from tchannel import TChannel as AsyncTchannel
    async_client = AsyncTchannel('s')
    with pytest.raises(BadRequestError):
        yield async_client.json(
            service='test-client',
            endpoint='hello',
            hostport=sync_client.hostport
        )

    sync_client.json.register(hello)
    with pytest.raises(BadRequestError):
        yield async_client.json(
            service='test-client',
            endpoint='hello',
            hostport=sync_client.hostport
        )


@pytest.mark.gen_test
def test_sync_register_thrift():
    sync_client = TChannel('test-client')

    ThriftTest = thrift.load(
        path='tests/data/idls/ThriftTest.thrift'
    ).SecondService

    @sync_client.json.register(ThriftTest)
    def blahBlah(request):
        pass

    sync_client.listen()

    from tchannel import TChannel as AsyncTchannel

    ThriftTest = thrift.load(
        path='tests/data/idls/ThriftTest.thrift',
        service='test-client',
        hostport=sync_client.hostport,
    ).SecondService

    async_client = AsyncTchannel('s')
    with pytest.raises(BadRequestError):
        yield async_client.thrift(
            ThriftTest.blahBlah(),
            hostport=sync_client.hostport
        )

    sync_client.json.register(blahBlah, ThriftTest)
    with pytest.raises(BadRequestError):
        yield async_client.thrift(
            ThriftTest.blahBlah(),
            hostport=sync_client.hostport,
        )
