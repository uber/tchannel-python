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
from tchannel.tornado.hyperbahn import AdvertiseError


@pytest.mark.integration
def test_sync_client_should_get_raw_response(tchannel_server):

    endpoint = 'health'
    tchannel_server.expect_call(endpoint).and_write(
        headers="",
        body="OK"
    )
    hostport = tchannel_server.tchannel.hostport

    client = TChannelSyncClient('test-client')
    request = client.request(hostport)

    future = request.send(endpoint, None, "")
    response = future.result()

    assert response.header == ""
    assert response.body == "OK"


@pytest.mark.integration
def test_advertise_should_result_in_peer_connections(tchannel_server):

    body = {"hello": "world"}

    tchannel_server.expect_call('ad', 'json').and_write(
        headers="",
        body=body,
    )

    routers = [
        tchannel_server.tchannel.hostport
    ]

    client = TChannelSyncClient('test-client')
    result = client.advertise(routers)

    assert result.header == ""
    # @todo https://github.com/uber/tchannel-python/issues/34
    assert result.body == json.dumps(body)
    assert client.async_client.peers.hosts == routers


def test_failing_advertise_should_raise(tchannel_server):

    tchannel_server.expect_call('ad', 'json').and_raise(
        Exception('great sadness')
    )

    routers = [
        tchannel_server.tchannel.hostport
    ]

    client = TChannelSyncClient('test-client')

    with pytest.raises(AdvertiseError):
        client.advertise(routers, timeout=0.005)
