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

import json

import pytest

from tchannel.sync import TChannelSyncClient
from tchannel.errors import TimeoutError


@pytest.mark.integration
def test_sync_client_should_get_raw_response(mock_server):

    endpoint = 'health'
    mock_server.expect_call(endpoint).and_write(
        headers="",
        body="OK"
    )
    hostport = mock_server.tchannel.hostport

    client = TChannelSyncClient('test-client')
    request = client.request(hostport)

    future = request.send(endpoint, None, "")
    response = future.result()

    assert response.header == ""
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

    client = TChannelSyncClient('test-client')
    result = client.advertise(routers)

    assert result.header == ""
    # @todo https://github.com/uber/tchannel-python/issues/34
    assert result.body == json.dumps(body)
    assert client._async_client.peers.hosts == routers


def test_failing_advertise_should_raise(mock_server):

    mock_server.expect_call('ad', 'json').and_raise(
        Exception('great sadness')
    )

    routers = [mock_server.tchannel.hostport]
    client = TChannelSyncClient('test-client')

    with pytest.raises(TimeoutError):
        client.advertise(routers, timeout=0.1)


def test_should_discover_ip():

    client = TChannelSyncClient('test-client')
    hostport = client._async_client.hostport

    assert '0.0.0.0:0' != hostport
