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
from thrift.Thrift import TType

from tchannel.serializer.thrift import ThriftSerializer
from tchannel.thrift.server import build_handler
from tchannel.thrift.server import deprecated_build_handler
from tchannel.tornado.request import Request
from tchannel.tornado.response import Response
from tchannel.tornado.stream import InMemStream


class FakeException(Exception):

    thrift_spec = (
        None,
        (1, TType.STRING, 'message', None, None),
    )

    def __init__(self, message=None):
        self.message = message

    def write(self, proto):
        proto.writeStructBegin('FakeException')

        if self.message is not None:
            proto.writeFieldBegin('message', TType.STRING, 1)
            proto.writeString(self.message)
            proto.writeFieldEnd()

        proto.writeFieldStop()
        proto.writeStructEnd()


class FakeResult(object):

    thrift_spec = (
        (0, TType.STRING, 'success', None, None),
        (
            1, TType.STRUCT, 'someException',
            (FakeException, FakeException.thrift_spec),
            None,
        ),
    )

    def __init__(self, success=None, someException=None):
        self.success = success
        self.someException = someException

    def read(self, proto):
        pass  # don't care

    def write(self, proto):
        proto.writeStructBegin('FakeResult')

        if self.success is not None:
            proto.writeFieldBegin('success', TType.STRING, 0)
            proto.writeString(self.success)
            proto.writeFieldEnd()

        if self.someException is not None:
            proto.writeFieldBegin('someException', TType.STRUCT, 1)
            self.someException.write(proto)
            proto.writeFieldEnd()

        proto.writeFieldStop()
        proto.writeStructEnd()


@pytest.mark.gen_test
def test_deprecated_build_handler():

    def call(treq, tres):
        assert treq.transport.headers == {
            'as': 'thrift', 'cn': 'test_caller'
        }

        tres.write_header('foo', 'baar')
        return "world"

    response_header = InMemStream()
    response_body = InMemStream()

    req = Request(
        argstreams=[
            InMemStream('hello'),
            InMemStream('\00\00'),  # no headers
            InMemStream('\00'),  # empty struct
        ],
        serializer=ThriftSerializer(FakeResult),
        headers={'cn': 'test_caller', 'as': 'thrift'},
    )
    req.close_argstreams()

    res = Response(
        argstreams=[
            InMemStream(),
            response_header,
            response_body,
        ],
        serializer=ThriftSerializer(FakeResult),
    )

    handler = deprecated_build_handler(FakeResult, call)
    yield handler(req, res)

    serialized_headers = yield response_header.read()
    assert serialized_headers == bytearray(
        [
            0x00, 0x01,  # num headers = 1
            0x00, 0x03,  # strlen('foo') = 3
        ] + list('foo') + [
            0x00, 0x04,  # strlen('baar') = 4
        ] + list('baar')
    )

    serialized_body = yield response_body.read()
    assert serialized_body == bytearray([
        0x0b,                    # field type = TType.STRING
        0x00, 0x00,              # field ID = 0
        0x00, 0x00, 0x00, 0x05,  # string length = 5
    ] + list("world") + [
        0x00,                    # end struct
    ])

    assert 0 == res.status_code


@pytest.mark.gen_test
def test_deprecated_build_handler_exception():
    def call(treq, tres):
        raise FakeException('fail')

    response_body = mock.Mock(spec=InMemStream)

    req = Request(
        argstreams=[
            InMemStream('hello'),
            InMemStream('\00\00'),  # no headers
            InMemStream('\00'),  # empty struct
        ],
        serializer=ThriftSerializer(FakeResult),
    )
    req.close_argstreams()

    res = Response(
        argstreams=[
            InMemStream(),
            InMemStream(),
            response_body,
        ],
        serializer=ThriftSerializer(FakeResult),
    )

    handler = deprecated_build_handler(FakeResult, call)
    yield handler(req, res)

    response_body.write.assert_called_once_with(
        bytearray([
            0x0c,                    # field type = TType.STRUCT
            0x00, 0x01,              # field ID = 1

            0x0b,                    # field type = TType.STRING
            0x00, 0x01,              # field ID = 1
            0x00, 0x00, 0x00, 0x04,  # string length = 5
        ] + list("fail") + [
            0x00,                    # end exception struct
            0x00,                    # end response struct
        ])
    )
    assert 1 == res.status_code


@pytest.mark.gen_test
def test_build_handler_application_exception():
    def call(req):
        raise FakeException('fail')

    req = Request(
        argstreams=[
            InMemStream('hello'),
            InMemStream('\00\00'),  # no headers
            InMemStream('\00'),  # empty struct
        ],
        serializer=ThriftSerializer(FakeResult),
    )
    req.close_argstreams()

    handler = build_handler(FakeResult, call)
    res = yield handler(req)

    assert res.status == 1
