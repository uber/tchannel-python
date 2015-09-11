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
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from tornado import gen

from tchannel.errors import ValueExpectedError
from tchannel.serializer.thrift import ThriftSerializer

from . import THRIFT


class ThriftArgScheme(object):
    """Handler registration and serialization for Thrift.

    To register a Thrift handler:

    .. code:: python

        @tchannel.thrift(GeneratedThriftModule)
        def method(request):
            print request.body.some_arg

    When calling a remote service, generated Thrift types need to be wrapped
    with :py:func:`thrift_request_builder` to provide TChannel compatibility:

    .. code:: python

        thrift_service = thrift_request_builder(
            service='service-identifier',
            thrift_module=GeneratedThriftModule,
        )

        response = yield tchannel.thrift(
            thrift_service.method(some_arg='foo'),
        )
    """

    NAME = THRIFT

    def __init__(self, tchannel):
        self._tchannel = tchannel

    @gen.coroutine
    def __call__(
        self,
        request,
        headers=None,
        timeout=None,
        retry_on=None,
        retry_limit=None,
        shard_key=None,
        trace=None,
    ):

        if not headers:
            headers = {}

        serializer = ThriftSerializer(request.result_type)
        # serialize
        try:
            headers = serializer.serialize_header(headers=headers)
        except (AttributeError, TypeError):
            raise ValueError(
                'headers must be a map[string]string (a shallow dict'
                ' where keys and values are strings)'
            )

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
            hostport=request.hostport,
            shard_key=shard_key,
            trace=trace,
        )

        # deserialize...
        response.headers = serializer.deserialize_header(
            headers=response.headers
        )
        body = serializer.deserialize_body(body=response.body)
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

    def register(self, thrift_module, **kwargs):

        return self._tchannel.register(
            scheme=self.NAME,
            endpoint=thrift_module,
            **kwargs
        )
