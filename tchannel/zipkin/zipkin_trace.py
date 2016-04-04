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

from tchannel.event import EventHook
from tchannel.zipkin import annotation
from tchannel.zipkin.tracers import DebugTracer
from tchannel.zipkin.tracers import TChannelZipkinTracer


class ZipkinTraceHook(EventHook):
    """generate zipkin-style span for tracing"""

    DEFAULT_RATE = 0.01

    def __init__(self, tchannel=None, dst=None, sample_rate=None):
        """Log zipkin style trace.

        :param tchannel:
            The tchannel instance to send zipkin trace spans
        :param dst:
            The destination to output trace information
        :param sample_rate:
            The sample_rate determines the probability that the trace span
            been sampled.
            The rate of sampling is in the range [0, 1] with 0.01 precision.
            By default it takes 100% sampling.
        """

        if tchannel:
            # TChannelZipkinTracer generates Base64-encoded span
            # and uploads to zipkin server
            self.tracer = TChannelZipkinTracer(tchannel)
        else:
            # DebugTracer generates json style span info and writes
            # to dst. By default it writes to stdout
            self.tracer = DebugTracer(dst)

        if sample_rate is None:
            sample_rate = self.DEFAULT_RATE

        assert 0 <= sample_rate <= 1
        self.rate = sample_rate
        self._check_point = self.rate * (1 << 64)

    def _lucky(self, id):
        return id < self._check_point

    def before_send_request(self, request):
        if not request.tracing.traceflags:
            return

        if not request.tracing.parent_span_id and not self._lucky(
            request.tracing.trace_id
        ):
            # disable trace
            request.tracing.traceflags = False
            return

        ann = annotation.client_send()
        request.tracing.annotations.append(ann)

    def before_receive_request(self, request):
        if not request.tracing.traceflags:
            return

        request.tracing.annotations.append(annotation.server_recv())

        caller_name = request.headers.get('cn')
        if caller_name:
            request.tracing.annotations.append(
                annotation.string('cn', caller_name),
            )

    def after_send_response(self, response):
        if not response.tracing.traceflags:
            return

        # send out a pair of annotations{server_recv, server_send} to zipkin
        ann = annotation.server_send()
        response.tracing.annotations.append(ann)
        self.tracer.record([(response.tracing, response.tracing.annotations)])

    def after_receive_response(self, request, response):
        if not response.tracing.traceflags:
            return

        # send out a pair of annotations{client_recv, client_send} to zipkin
        ann = annotation.client_recv()
        response.tracing.annotations.append(ann)
        self.tracer.record([(response.tracing, response.tracing.annotations)])

    def after_receive_error(self, request, error):
        if not error.tracing.traceflags:
            return

        ann = annotation.client_recv()
        error.tracing.annotations.append(ann)
        self.tracer.record([(error.tracing, error.tracing.annotations)])

    def after_send_error(self, error):
        if not error.tracing.traceflags:
            return

        ann = annotation.server_send()
        error.tracing.annotations.append(ann)
        self.tracer.record([(error.tracing, error.tracing.annotations)])
