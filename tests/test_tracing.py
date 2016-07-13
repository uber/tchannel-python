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

import json
import socket
import time
import traceback
import urllib

import mock
import opentracing
import pytest
import tornado
import tornado.gen
import tornado.testing
import tornado.web
from basictracer import BasicTracer
from basictracer.recorder import InMemoryRecorder
from opentracing import Format
from opentracing.ext import tags
from opentracing_instrumentation.client_hooks.tornado_http import (
    install_patches,
    reset_patchers
)
from opentracing_instrumentation.request_context import (
    span_in_stack_context,
    get_current_span
)
from tchannel import Response, thrift, TChannel, schemes
from tchannel.errors import BadRequestError
from tchannel.event import EventHook
from tornado import netutil
from tornado.httpclient import HTTPRequest

BAGGAGE_KEY = b'baggage'


# It seems under Travis the 'localhost' is bound to more then one IP address,
# which triggers a bug: https://github.com/tornadoweb/tornado/issues/1573
# Here we monkey-patch tornado/testing.py with the fix from
#   https://github.com/tornadoweb/tornado/pull/1574
def patched_bind_unused_port(reuse_port=False):
    sock = netutil.bind_sockets(None, '127.0.0.1', family=socket.AF_INET,
                                reuse_port=reuse_port)[0]
    port = sock.getsockname()[1]
    return sock, port


tornado.testing.bind_unused_port = patched_bind_unused_port


# noinspection PyShadowingNames
@pytest.fixture
def tracer():
    return BasicTracer(recorder=InMemoryRecorder())


@pytest.yield_fixture
def http_patchers():
    """Applies tracing monkey-patching to http libs"""
    install_patches.__original_func()  # install_patches func is a @singleton
    try:
        yield
    finally:
        reset_patchers()


@pytest.fixture
def thrift_service(tmpdir):
    thrift_file = tmpdir.join('service.thrift')
    thrift_file.write('''
        service X {
          string thrift1(1: string hostport), // calls thrift2()
          string thrift2(),
          string thrift3(1: string hostport)  // calls http
        }
    ''')

    return thrift.load(str(thrift_file), 'test-service')


def register(tchannel, thrift_service, http_client, base_url):
    @tchannel.json.register('endpoint1')
    @tornado.gen.coroutine
    def handler1(request):
        host_port = request.body
        res = yield tchannel.json(
            service='handler2',
            hostport=host_port,
            endpoint="endpoint2",
        )

        raise tornado.gen.Return(Response(res.body))

    @tchannel.thrift.register(thrift_service.X, method='thrift1')
    @tornado.gen.coroutine
    def thrift1(request):
        host_port = request.body.hostport
        res = yield tchannel.thrift(
            thrift_service.X.thrift2(),
            hostport=host_port,
        )
        raise tornado.gen.Return(Response(res.body))

    @tchannel.json.register('endpoint2')
    def handler2(_):
        return _extract_span()

    @tchannel.thrift.register(thrift_service.X, method='thrift2')
    def thrift2(_):
        return _extract_span()

    def _extract_span():
        span = get_current_span()
        if span:
            return span.context.get_baggage_item(BAGGAGE_KEY)
        return "baggage not found"

    @tchannel.json.register('endpoint3')
    def handler3(_):
        return _call_http()

    @tchannel.thrift.register(thrift_service.X, method='thrift3')
    def thrift3(_):
        return _call_http()

    @tornado.gen.coroutine
    def _call_http():
        response = yield http_client.fetch(base_url)
        if response.code != 200:
            raise Exception('Downstream http service returned code=%s: %s' % (
                response.code, response.body
            ))
        raise tornado.gen.Return(Response(body=response.body))


@pytest.fixture
def app():
    return tornado.web.Application()


# noinspection PyAbstractClass
class HttpHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super(HttpHandler, self).__init__(application, request, **kwargs)
        self.client_channel = kwargs['client_channel']

    def initialize(self, **kwargs):
        pass

    def _get_span(self):
        try:
            carrier = {}
            for k, v in self.request.headers.iteritems():
                carrier[k] = urllib.unquote(v)
            span_ctx = opentracing.tracer.extract(Format.TEXT_MAP, carrier)
            span = opentracing.tracer.start_span(
                operation_name='server',
                references=opentracing.child_of(span_ctx)
            )
        except Exception as e:
            self.write('ERROR: %s' % e)
            self.set_status(200)
            return None

        if span is None:
            self.write('ERROR: Failed to join trace')
            self.set_status(200)

        return span

    def get(self):
        span = self._get_span()
        if span:
            self.write(span.context.get_baggage_item(BAGGAGE_KEY))
            self.set_status(200)
            span.finish()

    @tornado.gen.coroutine
    def post(self):
        span = self._get_span()
        if span:
            try:
                with span_in_stack_context(span):
                    res = self.client_channel.json(
                        service='handler2',
                        hostport=self.request.body,
                        endpoint="endpoint2",
                    )
                res = yield res
                body = res.body
            except Exception as e:
                traceback.print_exc()
                self.write('ERROR: %s' % e)
                self.set_status(200)
                return
            else:
                self.write(body)
                self.set_status(200)
            finally:
                span.finish()


@pytest.mark.parametrize('endpoint,transport,encoding,enabled,expect_spans', [
    # tchannel(json)->tchannel(json)
    ('endpoint1', 'tchannel', 'json',   True,  5),
    ('endpoint1', 'tchannel', 'json',   False, 0),
    # tchannel(thrift)->tchannel(thrift)
    ('thrift1',   'tchannel', 'thrift', True,  5),
    ('thrift1',   'tchannel', 'thrift', False, 0),
    # tchannel(json)->http(json)
    ('endpoint3', 'tchannel', 'json',   True,  5),
    ('endpoint3', 'tchannel', 'json',   False, 0),
    # tchannel(thrift)->http(json)
    ('thrift3',   'tchannel', 'thrift', True,  5),
    ('thrift3',   'tchannel', 'thrift', False, 0),
    # http->tchannel
    ('/',         'http',     'json',   True,  5),
    ('/',         'http',     'json',   False, 0),
])
@pytest.mark.gen_test
def test_trace_propagation(
        endpoint, transport, encoding, enabled, expect_spans,
        http_patchers, tracer, mock_server, thrift_service,
        app, http_server, base_url, http_client):
    """
    Main TChannel-OpenTracing integration test, using basictracer as
    implementation of OpenTracing API.

    The main logic of this test is as follows:
      1. Start a new trace with a root span
      2. Store a random value in the baggage
      3. Call the first service at the endpoint from `endpoint` parameter.
         The first service is either tchannel or http, depending on the value
         if `transport` parameter.
      4. The first service calls the second service using pre-defined logic
         that depends on the endpoint invoked on the first service.
      5. The second service accesses the tracing span and returns the value
         of the baggage item as the response.
      6. The first service responds with the value from the second service.
      7. The main test validates that the response is equal to the original
         random value of the baggage, proving trace & baggage propagation.
      8. The test also validates that all spans have been finished and
         recorded, and that they all have the same trace ID.

    We expect 5 spans to be created from each test run:
      *  top-level (root) span started in the test
      *  client span (calling service-1)
      *  service-1 server span
      *  service-1 client span (calling service-2)
      *  service-2 server span

    :param endpoint: name of the endpoint to call on the first service
    :param transport: type of the first service: tchannel or http
    :param enabled: if False, channels are instructed to disable tracing
    :param expect_spans: number of spans we expect to be generated
    :param http_patchers: monkey-patching of tornado AsyncHTTPClient
    :param tracer: a concrete implementation of OpenTracing Tracer
    :param mock_server: tchannel server (from conftest.py)
    :param thrift_service: fixture that creates a Thrift service from fake IDL
    :param app: tornado.web.Application fixture
    :param http_server: http server (provided by pytest-tornado)
    :param base_url: address of http server (provided by pytest-tornado)
    :param http_client: Tornado's AsyncHTTPClient (provided by pytest-tornado)
    """
    # mock_server is created as a fixture, so we need to set tracer on it
    mock_server.tchannel._dep_tchannel._tracer = tracer
    mock_server.tchannel._dep_tchannel._trace = enabled

    register(tchannel=mock_server.tchannel, thrift_service=thrift_service,
             http_client=http_client, base_url=base_url)

    tchannel = TChannel(name='test', tracer=tracer, trace=enabled)

    app.add_handlers(".*$", [
        (r"/", HttpHandler, {'client_channel': tchannel})
    ])

    with mock.patch('opentracing.tracer', tracer):
        assert opentracing.tracer == tracer  # sanity check that patch worked

        span = tracer.start_span('root')
        baggage = 'from handler3 %d' % time.time()
        span.context.set_baggage_item(BAGGAGE_KEY, baggage)
        if not enabled:
            span.set_tag('sampling.priority', 0)
        with span:  # use span as context manager so that it's always finished
            response_future = None
            with tchannel.context_provider.span_in_context(span):
                if transport == 'tchannel':
                    if encoding == 'json':
                        response_future = tchannel.json(
                            service='test-client',
                            endpoint=endpoint,
                            hostport=mock_server.hostport,
                            body=mock_server.hostport,
                        )
                    elif encoding == 'thrift':
                        response_future = tchannel.thrift(
                            thrift_service.X.thrift1(mock_server.hostport),
                            hostport=mock_server.hostport,
                        )
                    else:
                        raise ValueError('wrong encoding %s' % encoding)
                elif transport == 'http':
                    response_future = http_client.fetch(
                        request=HTTPRequest(
                            url='%s%s' % (base_url, endpoint),
                            method='POST',
                            body=mock_server.hostport,
                        )
                    )
                else:
                    raise NotImplementedError(
                        'unknown transport %s' % transport)
            response = yield response_future

    body = response.body
    assert body == baggage

    def get_sampled_spans():
        return [s for s in tracer.recorder.get_spans() if s.context.sampled]

    # Sometimes the test runs into weird race condition where the
    # after_send_response() hook is executed, but the span is not yet
    # recorded. To prevent flaky test runs we check and wait until
    # all spans are recorded, for up to 1 second.
    for i in range(0, 1000):
        spans = get_sampled_spans()
        if len(spans) >= expect_spans:
            break
        yield tornado.gen.sleep(0.001)  # yield execution and sleep for 1ms

    spans = get_sampled_spans()
    assert expect_spans == len(spans), 'Unexpected number of spans reported'
    # We expect all trace IDs in collected spans to be the same
    spans = tracer.recorder.get_spans()
    assert 1 == len(set([s.context.trace_id for s in spans])), \
        'all spans must have the same trace_id'


# @pytest.mark.parametrize('ex_cls,start_span', [
#     (opentracing.UnsupportedFormatException, 0),
#     (opentracing.InvalidCarrierException, 0),
#     (opentracing.TraceCorruptedException, 1),
# ])
# def test_before_receive_request(ex_cls, start_span):
#     class Tracer(opentracing.Tracer):
#         def __init__(self):
#             super(Tracer, self).__init__()
#             self.span_started = 0
#
#         def join(self, operation_name, format, carrier):
#             raise ex_cls()
#
#         def start_span(self, operation_name=None,
#                        parent=None, tags=None, start_time=None):
#             self.span_started += 1
#             return super(Tracer, self).start_span(
#                 operation_name=operation_name)
#
#     log_fn = mock.Mock()
#     hook = OpenTracingHook(context_provider=None, tracer=Tracer(),
#                            log_exception_fn=log_fn)
#     hook.before_receive_request(request=mock.Mock())
#     assert log_fn.call_count == 1
#     assert hook.tracer.span_started == start_span
#
#
# @pytest.mark.gen_test
# def test_span_to_trace(tracer, mock_server):
#     """
#     In this test we verify that if the tracer implementation supports the
#     notions of trace_id, span_id, parent_id (similar to Zipkin) then we can
#     pass those IDs not just via the headers (primary OpenTracing propagation
#     mechanism), but also via TChannel's built-in tracing slot in the frame.
#     :param tracer: injected BasicTracer mixin
#     :param mock_server: injected TChannel mock server
#     """
#     def span_to_trace(span):
#         return {
#             'trace_id': span.context.trace_id,
#             'span_id': span.context.span_id,
#             'parent_span_id': span.context.parent_id,
#         }
#
#     context_provider = OpenTracingRequestContextProvider()
#     hook = OpenTracingHook(tracer=tracer, context_provider=context_provider,
#                            span_to_trace_fn=span_to_trace)
#
#     @mock_server.tchannel.raw.register('endpoint1')
#     @tornado.gen.coroutine
#     def handler1(request):
#         ctx = mock_server.tchannel.context_provider.get_current_context()
#         if hasattr(ctx, 'parent_tracing'):
#             res = ctx.parent_tracing.trace_id
#         else:
#             res = 'unknown'
#         raise tornado.gen.Return(Response('%s' % res))
#
#     tchannel = TChannel(name='test', context_provider=context_provider)
#     tchannel.hooks.register(hook)
#
#     with mock.patch('opentracing.tracer', tracer):
#         assert opentracing.tracer == tracer  # sanity check that patch worked
#         span = tracer.start_span('root')
#        with span:  # use span as context manager so that it's always finished
#             wrapper = SpanWrapper(span=span)
#             with context_provider.request_context(wrapper):
#                 response_future = tchannel.raw(
#                     service='test-client',
#                     hostport=mock_server.hostport,
#                     endpoint='endpoint1',
#                     headers=mock_server.hostport,
#                     trace=False,
#                 )
#             response = yield response_future
#         assert span.context.trace_id == long(response.body)


@pytest.mark.parametrize('encoding,operation', [
    ('json', 'foo'),
    ('thrift', 'X::thrift2'),
])
@pytest.mark.gen_test
def test_span_tags(encoding, operation, tracer, thrift_service):
    server = TChannel('server', tracer=tracer)
    server.listen()

    def get_span_baggage():
        sp = server.context_provider.get_current_span()
        baggage = sp.context.get_baggage_item('bender') if sp else None
        return {'bender': baggage}

    @server.json.register('foo')
    def handler(_):
        return get_span_baggage()

    @server.thrift.register(thrift_service.X, method='thrift2')
    def thrift2(_):
        return json.dumps(get_span_baggage())

    client = TChannel('client', tracer=tracer)

    span = tracer.start_span('root')
    span.context.set_baggage_item('bender', 'is great')
    with span:
        res = None
        with client.context_provider.span_in_context(span):
            if encoding == 'json':
                res = client.json(
                    service='test-service',  # match thrift_service name
                    endpoint='foo',
                    body={},
                    hostport=server.hostport,
                )
            elif encoding == 'thrift':
                res = client.thrift(
                    thrift_service.X.thrift2(),
                    hostport=server.hostport,
                )
            else:
                raise ValueError('Unknown encoding %s' % encoding)
        res = yield res  # cannot yield in StackContext
    res = res.body
    if isinstance(res, basestring):
        res = json.loads(res)
    assert res == {'bender': 'is great'}
    spans = tracer.recorder.get_spans()
    assert len(spans) == 3
    assert 1 == len(set([s.context.trace_id for s in spans])), \
        'all spans must have the same trace_id'
    parent = child = None
    for s in spans:
        if s.tags is None:
            continue
        if s.tags.get(tags.SPAN_KIND, None) == tags.SPAN_KIND_RPC_SERVER:
            child = s
        elif s.tags.get(tags.SPAN_KIND, None) == tags.SPAN_KIND_RPC_CLIENT:
            parent = s
    assert parent is not None
    assert child is not None
    assert parent.operation_name == operation
    assert child.operation_name == operation
    assert parent.tags.get(tags.PEER_SERVICE) == 'test-service'
    assert child.tags.get(tags.PEER_SERVICE) == 'client'
    assert parent.tags.get(tags.PEER_HOST_IPV4) is not None
    assert child.tags.get(tags.PEER_HOST_IPV4) is not None
    assert parent.tags.get('as') == encoding
    assert child.tags.get('as') == encoding


@pytest.mark.gen_test
def test_tracing_field_in_error_message():
    tchannel = TChannel('test')

    class ErrorEventHook(EventHook):
        def __init__(self):
            self.request_trace = None
            self.error_trace = None

        def before_receive_request(self, request):
            self.request_trace = request.tracing

        def after_send_error(self, error):
            self.error_trace = error.tracing

    hook = ErrorEventHook()
    tchannel.hooks.register(hook)

    tchannel.listen()

    with pytest.raises(BadRequestError):
        yield tchannel.call(
            scheme=schemes.RAW,
            service='test',
            arg1='endpoint',
            hostport=tchannel.hostport,
            timeout=1.0,  # used to be 0.02, but was unstable in Travis
        )

    assert hook.error_trace
    assert hook.request_trace
    assert hook.error_trace == hook.request_trace
