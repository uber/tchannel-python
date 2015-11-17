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

import mock
import pytest

from tchannel.errors import BadRequestError
from tchannel.glossary import MAX_SIZE_OF_ARG1
from tchannel.event import EventType
from tchannel.messages.error import ErrorCode
from tchannel.tornado.dispatch import RequestDispatcher
from tchannel.tornado import Request
from tchannel.tornado.stream import InMemStream


@pytest.fixture
def dispatcher():
    return RequestDispatcher(_handler_returns_response=True)


@pytest.fixture
def req():
    # FIXME: This is crazy for a unit test!!
    request = Request(
        argstreams=[
            InMemStream('foo'),
            InMemStream(),
            InMemStream(),
        ],
        headers={'as': 'raw'}
    )
    request.close_argstreams()
    return request


@pytest.fixture
def connection():
    return mock.MagicMock()


@pytest.mark.gen_test
def test_handle_call(dispatcher, req, connection):
    def handler(req):
        return 'bar'

    dispatcher.register('foo', handler)

    response = yield dispatcher.handle_call(req, connection)
    body = yield response.get_body()
    assert body == 'bar'


@pytest.mark.gen_test
def test_default_fallback_behavior(dispatcher, req, connection):
    """Undefined endpoints return 'Bad Request' errors."""
    yield dispatcher.handle_call(req, connection)
    assert connection.send_error.call_args[0][0].code == ErrorCode.bad_request


@pytest.mark.gen_test
def test_custom_fallback_behavior(dispatcher, req, connection):

    def handler(req):
        return 'bar'

    dispatcher.register(dispatcher.FALLBACK, handler)
    response = yield dispatcher.handle_call(req, connection)
    body = yield response.get_body()
    assert body == 'bar'


@pytest.mark.gen_test
def test_uncaught_exceptions_fire_event_hook(dispatcher, req, connection):

    def handler(req):
        raise Exception()

    dispatcher.register('foo', handler)

    yield dispatcher.handle_call(req, connection)

    connection.tchannel.event_emitter.fire.assert_called_with(
        EventType.on_exception,
        req,
        mock.ANY,
    )


@pytest.mark.gen_test
def test_server_arg1_limit(dispatcher, connection):
        request = Request(
            argstreams=[
                InMemStream('a'*MAX_SIZE_OF_ARG1 + 'a'),
                InMemStream(),
                InMemStream(),
            ],
        )
        request.close_argstreams()
        yield dispatcher.handle_call(request, connection)
        connection.send_error.assert_call_once_with(
            BadRequestError(
                'arg1 size is 16385 which exceeds the max size 16KB.'
            )
        )
