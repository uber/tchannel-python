from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport

from tchannel.schemes import THRIFT

from .. import io
from .. import rw


class ThriftSerializer(object):

    name = THRIFT

    _headers_rw = rw.headers(
        rw.number(2),
        rw.len_prefixed_string(rw.number(2)),
        rw.len_prefixed_string(rw.number(2)),
    )

    def __init__(self, deserialize_type):
        self.deserialize_type = deserialize_type

    def serialize_header(self, headers):
        headers = headers or {}
        result = self._headers_rw.write(headers, io.BytesIO()).getvalue()
        return result

    def deserialize_header(self, headers):
        headers = headers or {}
        headers = io.BytesIO(headers)
        headers = self._headers_rw.read(headers)
        result = dict(headers)

        return result

    def serialize_body(self, call_args):

        # TODO - use fastbinary directly
        #
        # fastbinary.encode_binary(
        #     call_args, (call_args.__class__, call_args.thrift_spec)
        # )
        # fastbinary.decode_binary(
        #    result, TMemoryBuffer(body),(result_type, result_type.thrift_spec)
        # )
        #
        trans = TTransport.TMemoryBuffer()
        proto = TBinaryProtocol.TBinaryProtocolAccelerated(trans)
        call_args.write(proto)
        result = trans.getvalue()

        return result

    def deserialize_body(self, body):
        trans = TTransport.TMemoryBuffer(body)
        proto = TBinaryProtocol.TBinaryProtocolAccelerated(trans)

        result = self.deserialize_type()
        result.read(proto)
        return result
