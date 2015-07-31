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


def serialize_header(headers):
    return _headers_rw.write(headers, io.BytesIO()).getvalue()


def deserialize_header(s):
    return _headers_rw.read(io.BytesIO(s))


def serialize_body(call_args):

    trans = TTransport.TMemoryBuffer()
    proto = TBinaryProtocol.TBinaryProtocolAccelerated(trans)
    call_args.write(proto)
    result = trans.getvalue()

    return result


def deserialize_body(s, result_type):

    trans = TTransport.TMemoryBuffer(s)
    proto = TBinaryProtocol.TBinaryProtocolAccelerated(trans)

    result = result_type()
    result.read(proto)
    return result
