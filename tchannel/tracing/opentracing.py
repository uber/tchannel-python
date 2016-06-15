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
import tchannel.event
import tchannel.zipkin.trace
from opentracing.ext import tags
from opentracing.propagation import Format


class SpanWrapper(tchannel.zipkin.trace.Trace):
    """
    An extension of Trace class that captures OpenTracing Span object.
    Normally TChannel stores Trace object in the request context so that
    tracing information is propagated from server endpoint to client call
    sites. By storing an OpenTracing span in the same context we can
    integrate with non-TChannel RPC calls.
    """
    def __init__(self, span, *args, **kwargs):
        super(SpanWrapper, self).__init__(*args, **kwargs)
        self.span = span

    @staticmethod
    def get_span(tracing):
        return getattr(tracing, 'span', None)


# noinspection PyBroadException
class OpenTracingHook(tchannel.event.EventHook):
    """
    Generates server and client tracing spans using OpenTracing API.

    See `tests/test_opentracing.py` for example of integration with
    HTTP servers and clients using `opentracing_instrumentation` package.
    """

    def __init__(self, context_provider, tracer=None,
                 span_to_trace_fn=None,
                 log_exception_fn=None):
        """Manage OpenTracing spans

        :param context_provider:
            TChannel's RequestContextProvider
        :param tracer:
            An instance of OpenTracing Tracer
        :param span_to_trace_fn:
            An optional, Tracer-specific function that extracts trace_id,
            span_id, parent_span_id from the Span in order to pass
            those to the constructor of the TChannel's Trace class.
            The function must return a dictionary with keys trace_id,
            span_id, and parent_span_id, where values are all i64.
        :param log_exception_fn:
            Zero-arg function used to log exceptions. Defaults to
            logging.exception('OpenTracing exception').
        """
        self.context_provider = context_provider
        self._tracer = tracer
        self.span_to_trace_fn = span_to_trace_fn
        if not log_exception_fn:
            log_exception_fn = (
                lambda: logging.exception('OpenTracing exception'))
        self.log_exception_fn = log_exception_fn

    @staticmethod
    def _operation_name(request):
        if hasattr(request, 'endpoint'):
            return request.endpoint
        else:
            return 'tchannel::call'

    @property
    def tracer(self):
        return self._tracer if self._tracer else opentracing.tracer

    def _get_current_span(self):
        context = self.context_provider.get_current_context()
        if context is None:
            return None
        span = getattr(context, 'span', None)
        if span:
            return span
        parent_tracing = getattr(context, 'parent_tracing', None)
        if not parent_tracing:
            return None
        return getattr(parent_tracing, 'span', None)

    def _span_to_trace(self, span):
        trace_kwargs = {}
        try:
            if self.span_to_trace_fn:
                ids = self.span_to_trace_fn(span)
                trace_kwargs = {
                    'trace_id': long(ids.get('trace_id', 1)),
                    'span_id': long(ids.get('span_id', 2)),
                    'parent_span_id': long(ids.get('parent_span_id', 1) or 1),
                }
        except:
            self.log_exception_fn()
        return trace_kwargs

    def before_send_request(self, request):
        try:
            parent_span = self._get_current_span()
            span = self.tracer.start_span(
                operation_name=self._operation_name(request),
                parent=parent_span
            )
            span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)
            if hasattr(request, 'service'):
                span.set_tag(tags.PEER_SERVICE, request.service)

            trace_kwargs = self._span_to_trace(span=span)
            request.tracing = SpanWrapper(
                span,
                trace_id=trace_kwargs.get('trace_id'),
                span_id=trace_kwargs.get('span_id'),
                parent_span_id=trace_kwargs.get('parent_span_id'),
                traceflags=0
            )

            # inject span into headers
            carrier = {}
            self.tracer.inject(span, Format.TEXT_MAP, carrier)
            for k, v in carrier.iteritems():
                request.headers[k] = v
        except:
            self.log_exception_fn()

    def after_receive_response(self, request, response):
        try:
            span = SpanWrapper.get_span(request.tracing)
            if span:
                span.finish()
        except:
            self.log_exception_fn()

    def after_receive_error(self, request, error):
        try:
            span = SpanWrapper.get_span(request.tracing)
            if span:
                span.set_tag('error', 'true')
                span.set_tag('exception', error)
                span.finish()
        except:
            self.log_exception_fn()

    def before_receive_request(self, request):
        try:
            span = None
            try:
                span = self.tracer.join(
                    operation_name=self._operation_name(request),
                    format=Format.TEXT_MAP,
                    carrier=request.headers
                )
            except opentracing.UnsupportedFormatException:
                self.log_exception_fn()
                return  # tracer does not support basic text format
            except opentracing.InvalidCarrierException:
                self.log_exception_fn()
                return  # tracer does not like headers
            except opentracing.TraceCorruptedException:
                self.log_exception_fn()
                pass  # we can still start a new span
            except:
                self.log_exception_fn()

            if span is None:
                span = self.tracer.start_span(
                    operation_name=self._operation_name(request),
                )

            if span:
                span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)
                caller_name = request.headers.get('cn')
                if caller_name:
                    span.set_tag(tags.PEER_SERVICE, caller_name)

                request.tracing = SpanWrapper(span)
        except:
            self.log_exception_fn()

    def after_send_response(self, response):
        try:
            span = SpanWrapper.get_span(response.tracing)
            if span:
                span.finish()
        except:
            self.log_exception_fn()

    def after_send_error(self, error):
        try:
            span = SpanWrapper.get_span(error.tracing)
            if span:
                span.set_tag('error', 'true')
                span.set_tag('exception', error)
                span.finish()
        except:
            self.log_exception_fn()
