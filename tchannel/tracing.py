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

import logging

import opentracing
import opentracing_instrumentation

from opentracing.ext import tags
from tchannel.messages import common, Tracing

log = logging.getLogger('tchannel')

# TRACING_KEY_PREFIX is used to prefix all keys used by the OpenTracing Tracer
# to represent its trace context and baggage. The prefixing is done in order
# to distinguish tracing headers from the actual application headers and to
# hide the former from the user code.
TRACING_KEY_PREFIX = '$tracing$'


# ZIPKIN_SPAN_FORMAT is a carrier format specifically designed for interop
# with TChannel. The inject operation expects a dictionary which is populated
# with (trace_id, span_id, parent_id, traceflags) attributes.  The extract
# operation expects either a dictionary or a tuple with the above attributes.
ZIPKIN_SPAN_FORMAT = 'zipkin-span-format'


# noinspection PyMethodMayBeStatic
class TracingContextProvider(object):
    """Tracks the OpenTracing Span currently in effect.

    Distributed tracing requires context propagation inside the application,
    so that outbound (downstream) calls can be part of the same trace as the
    inbound request.

    There are two ways to do this:

    * Pass some "context" object to every method that may need to use it.
      This has the best performance but is not always practical.

    * Store the "context" in a thread-local storage, so that it's always
      accessible from anywhere in the application.

    The asynchronous nature of Tornado means that multiple requests can be
    in-flight at any given moment, even in the same thread, so plain thread
    local storage does not work. This class provide an alternative to thread
    local storage by using Tornado's ``StackContext`` functionality.

    There's currently no way to disable Span tracking via ``StackContext``.
    """
    def get_current_span(self):
        """
        :return: The current :py:class:`Span` for this thread/request.
        """
        return opentracing_instrumentation.get_current_span()

    def span_in_context(self, span):
        """
        Store the `span` in the request context and return a `StackContext`.

        This method is meant to be used as a context manager:

        .. code-block:: python

            with tchannel.context_provider.span_in_context(span):
                f = handler_fn()
            res = yield f

        Note: StackContext does not allow yield when used a context manager.
        Instead, save the future and yield it outside of `with:` statement.

        :param span: an OpenTracing Span
        :return: ``StackContext``-based context manager
        """
        return opentracing_instrumentation.span_in_stack_context(span)


class ServerTracer(object):
    """Helper class for creating server-side spans."""

    __slots__ = ['tracer', 'operation_name', 'span']

    def __init__(self, tracer, operation_name):
        self.tracer = tracer
        self.operation_name = operation_name
        self.span = None

    def start_basic_span(self, request):
        """
        Start tracing span from the protocol's `tracing` fields.
        This will only work if the `tracer` supports Zipkin-style span context.

        :param request: inbound request
        :type request: tchannel.tornado.request.Request
        """
        # noinspection PyBroadException
        try:
            # Currently Java does not populate Tracing field, so do not
            # mistaken it for a real trace ID.
            if request.tracing.trace_id:
                context = self.tracer.extract(
                    format=ZIPKIN_SPAN_FORMAT,
                    carrier=request.tracing)
                self.span = self.tracer.start_span(
                    operation_name=request.endpoint,
                    child_of=context,
                    tags={tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER},
                )
        except opentracing.UnsupportedFormatException:
            pass  # tracer might not support Zipkin format
        except:
            log.exception('Cannot extract tracing span from Trace field')

    def start_span(self, request, headers, peer_host, peer_port):
        """
        Start a new server-side span. If the span has already been started
        by `start_basic_span`, this method only adds baggage from the headers.

        :param request: inbound tchannel.tornado.request.Request
        :param headers: dictionary containing parsed application headers
        :return:
        """
        parent_context = None
        # noinspection PyBroadException
        try:
            if headers and hasattr(headers, 'iteritems'):
                tracing_headers = {
                    k[len(TRACING_KEY_PREFIX):]: v
                    for k, v in headers.iteritems()
                    if k.startswith(TRACING_KEY_PREFIX)
                }
                parent_context = self.tracer.extract(
                    format=opentracing.Format.TEXT_MAP,
                    carrier=tracing_headers
                )
                if self.span and parent_context:
                    # we already started a span from Tracing fields,
                    # so only copy baggage from the headers.
                    for k, v in parent_context.baggage.iteritems():
                        self.span.set_baggage_item(k, v)
        except:
            log.exception('Cannot extract tracing span from headers')
        if self.span is None:
            self.span = self.tracer.start_span(
                operation_name=request.endpoint,
                child_of=parent_context,
                tags={tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER},
            )
        if 'cn' in request.headers:
            self.span.set_tag(tags.PEER_SERVICE, request.headers['cn'])
        if peer_host:
            self.span.set_tag(tags.PEER_HOST_IPV4, peer_host)
        if peer_port:
            self.span.set_tag(tags.PEER_PORT, peer_port)
        if 'as' in request.headers:
            self.span.set_tag('as', request.headers['as'])
        return self.span


class ClientTracer(object):
    """Helper class for creating client-side spans."""

    __slots__ = ['channel']

    def __init__(self, channel):
        self.channel = channel

    def start_span(self, service, endpoint, headers=None,
                   hostport=None, encoding=None):
        parent_span = self.channel.context_provider.get_current_span()
        parent_ctx = parent_span.context if parent_span else None
        span = self.channel.tracer.start_span(
            operation_name=endpoint,
            child_of=parent_ctx
        )
        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)
        span.set_tag(tags.PEER_SERVICE, service)
        set_peer_host_port(span, hostport)
        if encoding:
            span.set_tag('as', encoding)

        if headers is None:
            headers = {}
        if isinstance(headers, dict):
            # noinspection PyBroadException
            try:
                tracing_headers = {}
                self.channel.tracer.inject(
                    span.context, opentracing.Format.TEXT_MAP, tracing_headers)
                for k, v in tracing_headers.iteritems():
                    headers[TRACING_KEY_PREFIX + k] = v
            except:
                log.exception('Failed to inject tracing span into headers')

        return span, headers


def set_peer_host_port(span, hostport):
    if hostport:
        # noinspection PyBroadException
        try:
            host, port = hostport.split(':')
            span.set_tag(tags.PEER_HOST_IPV4, host)
            span.set_tag(tags.PEER_PORT, port)
        except:
            pass


def span_to_tracing_field(span):
    """
    Inject the span into Trace field, if Zipkin format is supported
    :param span: OpenTracing Span
    """
    if span is None:
        return common.random_tracing()
    # noinspection PyBroadException
    try:
        carrier = {}
        span.tracer.inject(span, ZIPKIN_SPAN_FORMAT, carrier)
        tracing = Tracing(span_id=carrier['span_id'],
                          trace_id=carrier['trace_id'],
                          parent_id=carrier['parent_id'] or 0L,
                          traceflags=carrier['traceflags'])
        return tracing
    except opentracing.UnsupportedFormatException:
        pass  # tracer might not support Zipkin format
    except:
        log.exception('Failed to inject tracing span into headers')
    return common.random_tracing()


def apply_trace_flag(span, trace, default_trace):
    """
    If ``trace`` (or ``default_trace``) is False, disables tracing on ``span``.
    :param span:
    :param trace:
    :param default_trace:
    :return:
    """
    if trace is None:
        trace = default_trace
    trace = trace() if callable(trace) else trace
    if trace is False and span:
        span.set_tag(tags.SAMPLING_PRIORITY, 0)


def api_check(tracer):
    tracer = tracer or opentracing.tracer
    assert not hasattr(tracer, 'join'), \
        'This version of TChannel requires opentracing>=1.1'
