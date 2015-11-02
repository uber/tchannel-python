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

from __future__ import absolute_import, unicode_literals, print_function

import pytest

from tchannel import thrift
from tchannel.thrift.rw import build_handler
from tchannel.request import Request, TransportHeaders
from tchannel.response import Response


@pytest.fixture
def module():
    return thrift.load('tests/data/idls/ThriftTest2.thrift', 'some_service')


@pytest.mark.gen_test
def test_build_handler(module):

    item = module.Item('foo', module.Value(stringValue='bar'))

    def call(request):
        assert request.transport.scheme == 'thrift'
        assert request.transport.caller_name == 'test_caller'
        assert request.body.key == 'key'

        return Response(body=item, headers={'foo': 'bar'})

    request = Request(
        body=module.Service.getItem('key').call_args,
        transport=TransportHeaders(
            scheme='thrift',
            caller_name='test_caller',
        ),
        endpoint='Service::getItem',
    )

    handler = build_handler(module.Service.getItem, call)
    response = yield handler(request)

    assert response.body.success == item
    assert response.headers == {'foo': 'bar'}
    assert response.status == 0


@pytest.mark.gen_test
def test_build_handler_application_exception(module):

    def call(request):
        raise module.ItemDoesNotExist('foo')

    request = Request(
        body=module.Service.getItem('key').call_args,
        endpoint='Service::getItem',
    )

    handler = build_handler(module.Service.getItem, call)
    response = yield handler(request)

    assert response.body.success is None
    assert response.body.doesNotExist == module.ItemDoesNotExist('foo')
    assert response.status == 1
