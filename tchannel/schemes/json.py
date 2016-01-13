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

from tornado import gen
from . import JSON
from ..serializer.json import JsonSerializer
from ..tracing import ClientTracer


class JsonArgScheme(object):
    """Semantic params and serialization for json."""

    NAME = JSON

    def __init__(self, tchannel):
        self._tchannel = tchannel
        self.tracer = ClientTracer(channel=tchannel)

    @gen.coroutine
    def __call__(
        self,
        service,
        endpoint,
        body=None,
        headers=None,
        timeout=None,
        retry_on=None,
        retry_limit=None,
        hostport=None,
        shard_key=None,
        trace=None,
        routing_delegate=None,
        caller_name=None,
    ):
        """Make JSON TChannel Request.

        .. code-block: python

            from tchannel import TChannel

            tchannel = TChannel('my-service')

            resp = tchannel.json(
                service='some-other-service',
                endpoint='get-all-the-crackers',
                body={
                    'some': 'dict',
                },
            )

        :param string service:
            Name of the service to call.
        :param string endpoint:
            Endpoint to call on service.
        :param string body:
            A raw body to provide to the endpoint.
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
        :param string hostport:
            A 'host:port' value to use when making a request directly to a
            TChannel service, bypassing Hyperbahn.
        :param routing_delegate:
            Name of a service to which the request router should forward the
            request instead of the service specified in the call req.
        :param caller_name:
            Name of the service making the request. Defaults to the name
            provided when the TChannel was instantiated.

        :rtype: Response
        """

        span, headers = self.tracer.start_span(
            service=service, endpoint=endpoint, headers=headers,
            hostport=hostport, encoding='json'
        )

        # serialize
        serializer = JsonSerializer()
        headers = serializer.serialize_header(headers)
        body = serializer.serialize_body(body)

        response = yield self._tchannel.call(
            scheme=self.NAME,
            service=service,
            arg1=endpoint,
            arg2=headers,
            arg3=body,
            timeout=timeout,
            retry_on=retry_on,
            retry_limit=retry_limit,
            hostport=hostport,
            shard_key=shard_key,
            trace=trace,
            tracing_span=span,  # span is finished in PeerClientOperation.send
            routing_delegate=routing_delegate,
            caller_name=caller_name,
        )

        # deserialize
        response.headers = serializer.deserialize_header(response.headers)
        response.body = serializer.deserialize_body(response.body)

        raise gen.Return(response)

    def register(self, endpoint, **kwargs):

        if callable(endpoint):
            handler = endpoint
            endpoint = None
        else:
            handler = None

        return self._tchannel.register(
            scheme=self.NAME,
            endpoint=endpoint,
            handler=handler,
            **kwargs
        )
