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

import time

import mock
import opentracing
import pytest
import tornado.web
import crossdock.server.api as api
from crossdock.server import server
from crossdock.server.api import Request, Downstream
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import InMemoryReporter
from tchannel import TChannel
from tornado.httpclient import HTTPRequest


def test_api_to_json():
    r = Request(serverRole='s2',
                downstream=Downstream(
                    serviceName='serviceName',
                    serverRole='s3',
                    encoding='json',
                    hostPort='localhost:123',
                    downstream=Downstream(
                        serviceName='serviceName',
                        serverRole='s4',
                        encoding='json',
                        hostPort='localhost:123',
                        downstream=None)))
    api.namedtuple_to_dict(r)


@pytest.fixture
def app():
    """Required by pytest-tornado's http_server fixture"""
    return tornado.web.Application()


# noinspection PyShadowingNames
@pytest.yield_fixture
def tracer():
    tracer = Tracer(
        service_name='test-tracer',
        sampler=ConstSampler(True),
        reporter=InMemoryReporter(),
    )
    try:
        yield tracer
    finally:
        tracer.close()


PERMUTATIONS = []
for s2 in ['json', 'thrift']:
    for s3 in ['json', 'thrift']:
        for sampled in [True, False]:
            PERMUTATIONS.append((s2, s3, sampled))


@pytest.mark.parametrize('s2_encoding,s3_encoding,sampled', PERMUTATIONS)
@pytest.mark.gen_test
def test_trace_propagation(
        s2_encoding, s3_encoding, sampled,
        app,
        mock_server,
        tracer,
        http_server, base_url, http_client):

    # mock_server is created as a fixture, so we need to set tracer on it
    mock_server.tchannel._dep_tchannel._tracer = tracer
    mock_server.tchannel._dep_tchannel._trace = True

    server.register_http_handlers(app)
    server.register_tchannel_handlers(mock_server.tchannel)

    # verify that server is ready
    yield http_client.fetch(
        request=HTTPRequest(
            url=base_url,
            method='HEAD',
        )
    )

    tchannel = TChannel(name='test', tracer=None, trace=True)

    level3 = Downstream(
        serviceName='python',
        serverRole='s3',
        encoding=s3_encoding,
        hostPort=mock_server.hostport,
        downstream=None,
    )

    level2 = Downstream(
        serviceName='python',
        serverRole='s2',
        encoding=s2_encoding,
        hostPort=mock_server.hostport,
        downstream=level3,
    )

    with mock.patch('opentracing.tracer', tracer):
        assert opentracing.tracer == tracer  # sanity check that patch worked

        span = tracer.start_span('root')
        baggage = 'some baggage %d' % time.time()
        span.set_baggage_item(api.BAGGAGE_KEY.encode('utf8'), baggage)
        if not sampled:
            span.set_tag('sampling.priority', 0)
        with span:  # use span as context manager so that it's always finished
            with tchannel.context_provider.span_in_context(span):
                observed_span = server.observe_span()
                response_future = server.call_downstream(
                    tchannel=tchannel,
                    target=level2,
                )
            response = yield response_future
    assert response.span == observed_span
    assert response.downstream is not None
    assert response.downstream.span == observed_span
    assert response.downstream.downstream is None
