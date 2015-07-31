from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from . import THRIFT


class ThriftArgScheme(object):

    NAME = THRIFT

    def __init__(self, tchannel):
        self._tchannel = tchannel

    @gen.coroutine
    def __call__(self, request=None, header=None, timeout=None):

        # serialize
        # ...

        body = None

        response = yield self._tchannel.call(
            scheme=self.NAME,
            service=request.service,
            arg1=request.endpoint,
            arg2=header,
            arg3=body
        )

        # deserialize
        # ...

        raise gen.Return(response)

    def stream(self):
        pass

    def register(self):
        pass
