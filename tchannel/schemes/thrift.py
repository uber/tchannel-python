from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from . import THRIFT
from tchannel.thrift.scheme import ThriftArgScheme as DepThriftSerializer


class ThriftArgScheme(object):

    NAME = THRIFT

    def __init__(self, tchannel):
        self._tchannel = tchannel

    @gen.coroutine
    def __call__(self, request=None, header=None, timeout=None, hostport=None):

        # serialize
        serializer = DepThriftSerializer(request.result_type)
        header = serializer.serialize_header(header)
        body = serializer.serialize_body(request.call_args)

        response = yield self._tchannel.call(
            scheme=self.NAME,
            service=request.service,
            arg1=request.endpoint,
            arg2=header,
            arg3=body,
            hostport=hostport
        )

        # deserialize
        response.header = serializer.deserialize_header(response.header)
        response.body = serializer.deserialize_body(response.body).success

        raise gen.Return(response)

    def stream(self):
        pass

    def register(self):
        pass
