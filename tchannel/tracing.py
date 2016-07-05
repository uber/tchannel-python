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

from opentracing.ext import tags as ext_tags
from tchannel.messages import common


log = logging.getLogger('tchannel')


class TracingContextProvider(object):
    """Tracks the OpenTracing Span currently in effect.

    Distributed tracing requires context propagation inside the application,
    do that outbound (downstream) calls can be part of the same trace as the
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
        :return: The current :py:class:`Span` for this thread.
        """
        return opentracing_instrumentation.get_current_span()

    def span_in_context(self, span):
        """
        Factory method meant to be used as a context manager:

        .. code-block:: python

            with tchannel.context_provider.span_in_context(span):
                handler_fn()

        :param span: an OpenTracing Span
        :return: ``StackContext``-based context manager
        """
        return opentracing_instrumentation.span_in_stack_context(span)


class ServerTracer(object):
    __slots__ = ['tracer', 'operation_name', 'span']

    def __init__(self, tracer, operation_name):
        self.tracer = tracer
        self.operation_name = operation_name
        self.span = None

    # noinspection PyMethodMayBeStatic
    def start_basic_span(self, tracing):
        """
        Starts tracing span from the protocol's `tracing` fields.

        This will only work if the `tracer` supports Zipkin-style span context.

        :param tracing: common.Tracing
        """
        # this is currently not implemented
        return self

    def start_span(self, request, headers):
        # TODO(ys) if self.span is already defined, merge baggage into it
        if self.span:
            return self.span
        operation_name = '%s:%s' % (request.service, request.endpoint)
        try:
            if headers:
                self.span = self.tracer.join(
                    operation_name=operation_name,
                    format=opentracing.Format.TEXT_MAP,
                    carrier=headers
                )
        except:
            log.exception('Cannot extract tracing span from headers')
        if not self.span:
            self.span = self.tracer.start_span(
                operation_name=operation_name
            )
        return self.span

def span_to_tracing_field(span):
    if span is None:
        return common.random_tracing()
    # TODO(ys) if tracer is Zipkin compatible, try to convert span to Tracing
    return common.random_tracing()


class ClientTracer(object):
    __slots__ = ['channel', 'operation_name', 'span']

    def __init__(self, channel):
        self.channel = channel

    def start_span(self, service, endpoint, headers):
        parent_span = self.channel.context_provider.get_current_span()
        span = self.channel.tracer.start_span(
            operation_name='%s:%s' % (service, endpoint),
            parent=parent_span
        )

        if headers is None:
            headers = {}
        if isinstance(headers, dict):
            try:
                self.channel.tracer.inject(
                    span, opentracing.Format.TEXT_MAP, headers)
            except:
                log.exception('Failed to inject tracing span into headers')
        return span, headers

    def apply_trace_flag(self, span, traceflag):
        traceflag = traceflag() if callable(traceflag) else traceflag
        if traceflag is False and span:
            span.set_tag(ext_tags.SAMPLING_PRIORITY, 0)
