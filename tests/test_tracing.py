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

import threading

import pytest
from basictracer import BasicTracer, SpanRecorder
from tchannel import TChannel


@pytest.fixture
def span_recorder():
    class InMemoryRecorder(SpanRecorder):
        def __init__(self):
            self.spans = []
            self.mux = threading.Lock()

        def record_span(self, span):
            with self.mux:
                self.spans.append(span)

        def get_spans(self):
            with self.mux:
                return self.spans[:]

    return InMemoryRecorder()


# noinspection PyShadowingNames
@pytest.fixture
def tracer(span_recorder):
    return BasicTracer(recorder=span_recorder)


@pytest.mark.gen_test
def test_tracing_json(tracer):
    server = TChannel('server', tracer=tracer)
    server.listen()

    @server.json.register('foo')
    def handler(request):
        assert request.headers['header1'] == 'header-value1'
        span = server.context_provider.get_current_span()
        baggage = span.get_baggage_item('bender') if span else None
        return {'bender': baggage}

    client = TChannel('client', known_peers=[server.hostport], tracer=tracer)

    span = tracer.start_span('root')
    span.set_baggage_item('bender', 'is great')
    with client.context_provider.span_in_context(span):
        res = client.json(
            service='service',
            endpoint='foo',
            body={},
            headers={'header1': 'header-value1'},
        )
    res = yield res  # cannot yield in StackContext
    assert res.body == {'bender': 'is great'}
