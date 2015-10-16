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

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from ...util import get_thrift_file

from tchannel import TChannel
from tchannel import thrift


@pytest.fixture
def keyvalue(tmpdir, request):
    thrift_file = get_thrift_file(tmpdir)
    return thrift.load(request.node.name, str(thrift_file))


@pytest.fixture
def server(keyvalue, request, io_loop):  # need io_loop for server to work
    Service = keyvalue.Service
    server = TChannel(request.node.name + '.server')

    @server.thrift.register(Service)
    def getItem(request):
        return keyvalue.Item('hello', keyvalue.Value(stringValue='foo'))

    @server.thrift.register(Service)
    def putItem(request):
        raise keyvalue.ItemAlreadyExists(
            keyvalue.Item('hello', keyvalue.Value(stringValue='foo')),
            'this item already exists',
        )

    server.listen()
    return server


@pytest.fixture(params=[True, False], ids=['known_peers', 'hostport'])
def call(request, server):
    if request.param:
        # use known_peers
        return TChannel(
            request.node.name + '.client',
            known_peers=[server.hostport]
        ).thrift
    else:
        # use hostport kwarg

        client = TChannel(request.node.name + '.client')

        def f(*args, **kwargs):
            return client.thrift(*args, hostport=server.hostport, **kwargs)

        return f


@pytest.mark.gen_test
def test_call_success(keyvalue, call):
    response = yield call(
        keyvalue.Service.getItem('foo')
    )
    assert response.body == keyvalue.Item(
        'hello', keyvalue.Value(stringValue='foo')
    )


@pytest.mark.gen_test
def test_call_thrift_exception(keyvalue, call):
    with pytest.raises(keyvalue.ItemAlreadyExists) as exc_info:
        yield call(
            keyvalue.Service.putItem(
                keyvalue.Item('hello', keyvalue.Value(stringValue='foo')),
                True,
            )
        )

    assert 'this item already exists' in str(exc_info)
