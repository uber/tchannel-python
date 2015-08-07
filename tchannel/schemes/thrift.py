from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from . import THRIFT
from tchannel.errors import ValueExpectedError
from tchannel.thrift import serializer


class ThriftArgScheme(object):
    """Semantic params and serialization for Thrift."""

    NAME = THRIFT

    def __init__(self, tchannel):
        self._tchannel = tchannel

    @gen.coroutine
    def __call__(self, request, headers=None, timeout=None,
                 retry_on=None, retry_limit=None):

        assert request, "a ThriftRequest is required"

        if headers is None:
            headers = {}

        # serialize
        headers = serializer.serialize_headers(headers=headers)
        body = serializer.serialize_body(call_args=request.call_args)

        response = yield self._tchannel.call(
            scheme=self.NAME,
            service=request.service,
            arg1=request.endpoint,
            arg2=headers,
            arg3=body,
            timeout=timeout,
            retry_on=retry_on,
            retry_limit=retry_limit,
            hostport=request.hostport
        )

        # deserialize...

        response.headers = serializer.deserialize_headers(
            headers=response.headers
        )
        body = serializer.deserialize_body(
            body=response.body,
            result_type=request.result_type
        )
        result_spec = request.result_type.thrift_spec

        # raise application exception, if present
        for exc_spec in result_spec[1:]:
            exc = getattr(body, exc_spec[2])
            if exc is not None:
                raise exc

        # success - non-void
        if len(result_spec) >= 1 and result_spec[0] is not None:

            # value expected, but got none
            # TODO - server side should use this same logic
            if body.success is None:
                raise ValueExpectedError(
                    'Expected a value to be returned for %s, '
                    'but recieved None - only void procedures can'
                    'return None.' % request.endpoint
                )

            response.body = body.success
            raise gen.Return(response)

        # success - void
        else:
            response.body = None
            raise gen.Return(response)
