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

        serializer = request.get_serializer()

        # serialize
        try:
            headers = serializer.serialize_header(headers=headers)
        except (AttributeError, TypeError):
            raise ValueError(
                'headers must be a map[string]string (a shallow dict'
                ' where keys and values are strings)'
            )

        body = serializer.serialize_body(request.call_args)

        # TODO There's only one yield. Drop in favor of future+callback.
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

        response.headers = serializer.deserialize_header(
            headers=response.headers
        )
        body = serializer.deserialize_body(body=response.body)

        response.body = request.read_body(body)
        raise gen.Return(response)

    def register(self, thrift_module, **kwargs):
        # dat circular import
        from tchannel.thrift import rw as thriftrw

        if isinstance(thrift_module, thriftrw.Service):
            # Dirty hack to support thriftrw and old API
            return thriftrw.register(
                # TODO drop deprecated tchannel
                self._tchannel._dep_tchannel._handler,
                thrift_module,
                **kwargs
            )
        else:
            return self._tchannel.register(
                scheme=self.NAME,
                endpoint=thrift_module,
                **kwargs
            )
