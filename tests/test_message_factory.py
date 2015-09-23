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

from tchannel.messages import CallRequestMessage
from tchannel.messages import CallResponseMessage
from tchannel.messages import ErrorMessage
from tchannel.messages.common import FlagsType
from tchannel.messages.common import StreamState
from tchannel.tornado import Request
from tchannel.tornado import Response
from tchannel.tornado.message_factory import MessageFactory
from tchannel.tornado.response import StatusCode
from tchannel.zipkin.trace import Trace


def test_build_raw_request_message():
    message_factory = MessageFactory()
    req = Request(
        ttl=32,
        service="test",
        headers={},
        id=1111,
    )
    req.state = StreamState.init
    message = message_factory.build_raw_request_message(req, None, True)
    assert message.ttl / 1000.0 == req.ttl
    assert message.flags == req.flags
    assert message.id == req.id
    assert message.service == req.service
    assert message.headers == req.headers


def test_build_raw_response_message():
    message_factory = MessageFactory()
    resp = Response(
        flags=FlagsType.none,
        code=StatusCode.ok,
        headers={},
        tracing=Trace(),
        id=1111,
    )
    resp.state = StreamState.init
    message = message_factory.build_raw_response_message(resp, None, True)
    assert message.code == resp.code
    assert message.flags == resp.flags
    assert message.id == resp.id
    assert message.headers == resp.headers


def test_build_request():
    message_factory = MessageFactory()
    message = CallRequestMessage(
        flags=FlagsType.none,
        ttl=100,
        service="test",
        headers={},
        id=12,
    )

    req = message_factory.build_request(message)
    assert req.ttl == message.ttl / 1000.0
    assert req.flags == message.flags
    assert req.headers == message.headers
    assert req.id == message.id
    assert req.service == message.service


def test_build_response():
    message_factory = MessageFactory()
    message = CallResponseMessage(
        flags=FlagsType.none,
        code=StatusCode.ok,
        headers={},
        id=12,
    )

    req = message_factory.build_response(message)
    assert req.code == message.code
    assert req.flags == message.flags
    assert req.headers == message.headers
    assert req.id == message.id


def test_build_inbound_error():
    message = ErrorMessage(code=0, tracing=Trace(), description="test")
    error = MessageFactory.build_inbound_error(message)

    assert error.code == message.code
    assert error.description == message.description
    assert error.tracing == message.tracing
