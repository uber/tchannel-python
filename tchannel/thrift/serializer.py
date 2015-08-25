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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport

from .. import io
from .. import rw

_headers_rw = rw.headers(
    rw.number(2),
    rw.len_prefixed_string(rw.number(2)),
    rw.len_prefixed_string(rw.number(2)),
)


def serialize_headers(headers):

    result = _headers_rw.write(headers, io.BytesIO()).getvalue()

    return result


def deserialize_headers(headers):

    headers = io.BytesIO(headers)
    headers = _headers_rw.read(headers)
    result = dict(headers)

    return result


def serialize_body(call_args):

    # TODO - use fastbinary directly
    #
    # fastbinary.encode_binary(
    #     call_args, (call_args.__class__, call_args.thrift_spec)
    # )
    # fastbinary.decode_binary(
    #     result, TMemoryBuffer(body), (result_type, result_type.thrift_spec)
    # )
    #
    trans = TTransport.TMemoryBuffer()
    proto = TBinaryProtocol.TBinaryProtocolAccelerated(trans)
    call_args.write(proto)
    result = trans.getvalue()

    return result


def deserialize_body(body, result_type):

    trans = TTransport.TMemoryBuffer(body)
    proto = TBinaryProtocol.TBinaryProtocolAccelerated(trans)

    result = result_type()
    result.read(proto)
    return result
