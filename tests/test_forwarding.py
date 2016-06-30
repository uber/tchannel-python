# Copyright (c) 2016 Uber Technologies, Inc.
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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
from tornado import gen

from tchannel import TChannel, thrift


@pytest.fixture
def keyvalue_data():
    return {}


@pytest.fixture
def keyvalue(tmpdir):
    path = tmpdir.join('keyvalue.thrift')
    path.write('''
        exception ItemDoesNotExist {
            1: optional string key
        }

        service KeyValue {
            string getItem(1: string key)
                throws (1: ItemDoesNotExist doesNotExist)
        }
    ''')

    return thrift.load(str(path), service='keyvalue')


@pytest.fixture
def keyvalue_server(io_loop, keyvalue, keyvalue_data):
    server = TChannel(name='keyvalue')
    server.listen()

    @server.thrift.register(keyvalue.KeyValue)
    def getItem(request):
        assert request.service == 'keyvalue'
        key = request.body.key
        if key in keyvalue_data:
            assert request.headers == {'expect': 'success'}
            return keyvalue_data[key]
        else:
            assert request.headers == {'expect': 'failure'}
            raise keyvalue.ItemDoesNotExist(key)

    @server.json.register('putItem')
    def json_put_item(request):
        assert request.service == 'keyvalue'
        assert request.timeout == 0.5
        key = request.body['key']
        value = request.body['value']
        keyvalue_data[key] = value
        return {'success': True}

    return server


@pytest.fixture
def proxy_server(keyvalue_server):
    server = TChannel(name='keyvalue-proxy')
    server.listen()

    # The client that the proxy uses to make requests should be a different
    # TChannel. That's because TChannel treats all peers (incoming and
    # outgoing) as the same. So, if the server receives a request and then
    # uses the same channel to make the request, there's a chance that it gets
    # forwarded back to the peer that originally made the request.
    #
    # This is desirable behavior because we do want to treat all Hyperbahn
    # nodes as equal.
    proxy_server_client = TChannel(
        name='proxy-client', known_peers=[keyvalue_server.hostport],
    )

    @server.register(TChannel.FALLBACK)
    @gen.coroutine
    def handler(request):
        response = yield proxy_server_client.call(
            scheme=request.transport.scheme,
            service=request.service,
            arg1=request.endpoint,
            arg2=request.headers,
            arg3=request.body,
            timeout=request.timeout / 2,
            retry_on=request.transport.retry_flags,
            retry_limit=0,
            shard_key=request.transport.shard_key,
            routing_delegate=request.transport.routing_delegate,
        )
        raise gen.Return(response)

    return server


@pytest.fixture
def client(proxy_server):
    return TChannel(name='client', known_peers=[proxy_server.hostport])


@pytest.mark.gen_test
def test_forwarding_thrift_exception(keyvalue, client):
    with pytest.raises(keyvalue.ItemDoesNotExist):
        yield client.thrift(
            keyvalue.KeyValue.getItem('foo'),
            headers={'expect': 'failure'},
        )


@pytest.mark.gen_test
def test_forwarding_thrift_exception_raw(keyvalue, client):
    response = yield client.call(
        scheme='thrift',
        service='keyvalue',
        arg1='KeyValue::getItem',
        arg2=b'\x00\x01\x00\x06expect\x00\x07failure',
        arg3=b'\x0B\x00\x01\x00\x00\x00\x03foo\x00',
    )

    assert b'\x00\x00' == response.headers
    assert bytearray([
        0x0c, 0x00, 0x01,  # 1: ItemDoesNotExist doesNotExist
        0x0b, 0x00, 0x01,  # 1: string key
        0x00, 0x00, 0x00, 0x03,  # "foo"
        0x66, 0x6f, 0x6f,
        0x00,  # end
        0x00,  # end
    ]) == response.body
    assert 1 == response.status


@pytest.mark.gen_test
def test_forwarding_thrift_success(keyvalue, client, keyvalue_data):
    keyvalue_data['hello'] = 'world'
    response = yield client.thrift(
        keyvalue.KeyValue.getItem('hello'),
        headers={'expect': 'success'},
    )
    assert response.body == 'world'


@pytest.mark.gen_test
def test_forwarding_json(client):
    json_response = yield client.json('keyvalue', 'putItem', {
        'key': 'hello',
        'value': 'world',
    }, timeout=1.0)
    assert json_response.body == {'success': True}
