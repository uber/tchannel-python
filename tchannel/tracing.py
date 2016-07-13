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
from tchannel.messages import common


log = logging.getLogger('tchannel')


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

    # noinspection PyMethodMayBeStatic
    def start_basic_span(self, tracing):
        """
        Start tracing span from the protocol's `tracing` fields.

        This will only work if the `tracer` supports Zipkin-style span context.

        :param tracing: common.Tracing
        """
        pass  # TODO(ys) implement start_basic_span

    def start_span(self, request, headers, peer_host, peer_port):
        """
        Start a new server-side span. If the span has already been started
        by `start_basic_span`, this method only adds baggage from the headers.

        :param request: inbound tchannel.tornado.request.Request
        :param headers: dictionary containing parsed application headers
        :return:
        """
        if self.span:
            # TODO(ys) if self.span is already defined, merge baggage into it
            return self.span
        # noinspection PyBroadException
        parent_ref = None
        try:
            if headers:
                parent = self.tracer.extract(
                    format=opentracing.Format.TEXT_MAP,
                    carrier=headers
                )
                if parent:
                    parent_ref = opentracing.ChildOf(parent)
        except:
            log.exception('Cannot extract tracing span from headers')
        self.span = self.tracer.start_span(
            operation_name=request.endpoint,
            references=parent_ref
        )
        self.span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)
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

    def start_span(self, service, endpoint, headers,
                   hostport=None, encoding=None):
        parent_span = self.channel.context_provider.get_current_span()
        parent_ref = None if parent_span is None else opentracing.ChildOf(
            parent_span.context)
        span = self.channel.tracer.start_span(
            operation_name=endpoint,
            references=parent_ref
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
                self.channel.tracer.inject(
                    span.context, opentracing.Format.TEXT_MAP, headers)
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
    if span is None:
        return common.random_tracing()
    # TODO(ys) if tracer is Zipkin compatible, try to convert span to Tracing
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
