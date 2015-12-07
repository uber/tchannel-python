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

from tchannel import TChannel
from tchannel import thrift
from tchannel.serializer.raw import RawSerializer
from tchannel.tornado.dispatch import RequestDispatcher


def dummy_endpoint(request, response):
    pass


def test_dispatch():
    dispatcher = RequestDispatcher()

    dispatcher.register(
        r"/hello",
        dummy_endpoint,
        RawSerializer(),
        RawSerializer(),
    )

    endpoint = dispatcher.handlers.get("/hello")[0]
    assert endpoint == dummy_endpoint


@pytest.mark.gen_test
def test_routing_delegate_is_propagated_raw():
    server = TChannel('server')
    server.listen()

    @server.raw.register('foo')
    def handler(request):
        assert request.transport.routing_delegate == 'delegate'
        return b'success'

    client = TChannel('client', known_peers=[server.hostport])
    res = yield client.raw('service', 'foo', b'', routing_delegate='delegate')
    assert res.body == b'success'


@pytest.mark.gen_test
def test_routing_delegate_is_propagated_json():
    server = TChannel('server')
    server.listen()

    @server.json.register('foo')
    def handler(request):
        assert request.transport.routing_delegate == 'delegate'
        return {'success': True}

    client = TChannel('client', known_peers=[server.hostport])
    res = yield client.json('service', 'foo', {}, routing_delegate='delegate')
    assert res.body == {'success': True}


@pytest.mark.gen_test
def test_routing_delegate_is_propagated_thrift(tmpdir):
    tmpdir.join('service.thrift').write('service Service { bool healthy() }')
    thrift_module = thrift.load(str(tmpdir.join('service.thrift')),
                                service='service')

    server = TChannel('server')
    server.listen()

    @server.thrift.register(thrift_module.Service)
    def healthy(request):
        assert request.transport.routing_delegate == 'delegate'
        return True

    client = TChannel('client', known_peers=[server.hostport])
    res = yield client.thrift(
        thrift_module.Service.healthy(), routing_delegate='delegate'
    )
    assert res.body is True
