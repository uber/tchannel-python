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

import base64
import json

import pytest
import tornado
import tornado.gen

from tchannel import TChannel, Response
from tchannel.zipkin.annotation import Endpoint
from tchannel.zipkin.annotation import client_send
from tchannel.zipkin.tcollector import TCollector
from tchannel.zipkin.tcollector import Response as TResponse
from tchannel.zipkin.trace import Trace
from tchannel.zipkin.tracers import TChannelZipkinTracer
from tchannel.zipkin.zipkin_trace import ZipkinTraceHook
from tests.mock_server import MockServer

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


def register(tchannel):

    @tchannel.raw.register('endpoint1')
    @tornado.gen.coroutine
    def handler1(request):
        hostport = request.headers

        res = yield tchannel.raw(
            service='handler2',
            hostport=hostport,
            endpoint="endpoint2",
        )

        raise tornado.gen.Return(Response(res.body, "from handler1"))

    @tchannel.raw.register('endpoint2')
    @tornado.gen.coroutine
    def handler2(request):
        return "from handler2"

    @tchannel.thrift.register(TCollector)
    def submit(request):
        span = request.body.span
        ok = request.transport.shard_key == base64.b64encode(span.traceId)
        return TResponse(ok=ok)


trace_buf = StringIO()


@pytest.yield_fixture
def trace_server():
    with MockServer() as server:
        register(server.tchannel)
        server.tchannel.hooks.register(
            ZipkinTraceHook(
                dst=trace_buf,
            ),
        )
        yield server


@pytest.mark.gen_test
def test_zipkin_trace(trace_server):
    endpoint = b'endpoint1'
    zipkin_tracer = ZipkinTraceHook(dst=trace_buf)
    tchannel = TChannel(name='test')
    tchannel.hooks.register(zipkin_tracer)

    hostport = 'localhost:%d' % trace_server.port

    response = yield tchannel.raw(
        service='test-client',
        hostport=hostport,
        endpoint=endpoint,
        headers=hostport,
        trace=True,
    )

    header = response.headers
    body = response.body
    assert header == "from handler1"
    assert body == "from handler2"
    traces = []
    for trace in trace_buf.getvalue().split("\n"):
        if trace:
            traces.append(json.loads(trace))

    parent_span_id = object()
    trace_id = traces[0][0][u'trace_id']

    assert traces

    for trace in traces:
        assert trace_id == trace[0][u'trace_id']
        if trace[0][u'name'] == u'endpoint2':
            parent_span_id = trace[0][u'parent_span_id']
        else:
            span_id = trace[0][u'span_id']

    assert parent_span_id == span_id


@pytest.mark.gen_test
def test_tcollector_submit(trace_server):
    tchannel = TChannel(name='test', known_peers=[trace_server.hostport])

    trace = Trace(
        name='endpoint', endpoint=Endpoint('1.0.0.1', 1111, 'tcollector')
    )
    anns = [client_send()]

    results = yield TChannelZipkinTracer(tchannel).record([(trace, anns)])

    assert results[0].body.ok is True
