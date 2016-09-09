# Copyright (c) 2016 Uber Technologies, Inc.
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

from tchannel.tracing import ClientTracer
from tornado import gen

from . import THRIFT


class ThriftArgScheme(object):
    """Handler registration and serialization for Thrift.

    Use :py:func:`tchannel.thrift.load` to parse your Thrift IDL and compile
    it into a module dynamically.

    .. code:: python

        from tchannel import thrift

        keyvalue = thrift.load('keyvalue.thrift', service='keyvalue')

    To register a Thrift handler, use the ``register()`` decorator, providing
    a reference to the compiled service as an argument. The name of the
    service method should match the name of the decorated function.

    .. code:: python

        tchannel = TChannel(...)

        @tchannel.thrift.register(keyvalue.KeyValue)
        def setValue(request):
            data[request.body.key] = request.body.value

    Use methods on the compiled service to generate requests to remote
    services and execute them via ``TChannel.thrift()``.

    .. code:: python

        response = yield tchannel.thrift(
            keyvalue.KeyValue.setValue(key='foo', value='bar')
        )
    """

    NAME = THRIFT

    def __init__(self, tchannel):
        self._tchannel = tchannel
        self.tracer = ClientTracer(channel=tchannel)

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
        hostport=None,
        routing_delegate=None,
        caller_name=None,
    ):
        """Make a Thrift TChannel request.

        Returns a ``Response`` containing the return value of the Thrift
        call (if any). If the remote server responded with a Thrift exception,
        that exception is raised.

        :param string request:
            Request obtained by calling a method on service objects generated
            by :py:func:`tchannel.thrift.load`.
        :param dict headers:
            Dictionary of header key-value pairs.
        :param float timeout:
            How long to wait (in seconds) before raising a ``TimeoutError`` -
            this defaults to ``tchannel.glossary.DEFAULT_TIMEOUT``.
        :param string retry_on:
            What events to retry on - valid values can be found in
            ``tchannel.retry``.
        :param int retry_limit:
            How many attempts should be made (in addition to the initial
            attempt) to re-send this request when retryable error conditions
            (specified by ``retry_on``) are encountered.

            Defaults to ``tchannel.retry.DEFAULT_RETRY_LIMIT`` (4).

            Note that the maximum possible time elapsed for a request is thus
            ``(retry_limit + 1) * timeout``.
        :param string shard_key:
            Set the ``sk`` transport header for Ringpop request routing.
        :param int trace:
            Flags for tracing.
        :param string hostport:
            A 'host:port' value to use when making a request directly to a
            TChannel service, bypassing Hyperbahn. This value takes precedence
            over the ``hostport`` specified to
            :py:func:`tchannel.thrift.load`.
        :param routing_delegate:
            Name of a service to which the request router should forward the
            request instead of the service specified in the call req.
        :param caller_name:
            Name of the service making the request. Defaults to the name
            provided when the TChannel was instantiated.

        :rtype: Response
        """
        if not headers:
            headers = {}

        span, headers = self.tracer.start_span(
            service=request.service, endpoint=request.endpoint,
            headers=headers, hostport=hostport, encoding='thrift'
        )

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
            hostport=hostport or request.hostport,
            shard_key=shard_key,
            trace=trace,
            tracing_span=span,  # span is finished in PeerClientOperation.send
            routing_delegate=routing_delegate,
            caller_name=caller_name,
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
