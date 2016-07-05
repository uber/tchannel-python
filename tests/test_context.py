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

# from __future__ import absolute_import
#
# import threading
#
# import pytest
# from basictracer import BasicTracer, SpanRecorder
# from tchannel import Response
# from tchannel import TChannel
# from tchannel import schemes
# from tornado import gen
#
#
# @pytest.fixture
# def span_recorder():
#     class InMemoryRecorder(SpanRecorder):
#         def __init__(self):
#             self.spans = []
#             self.mux = threading.Lock()
#
#         def record_span(self, span):
#             with self.mux:
#                 self.spans.append(span)
#
#         def get_spans(self):
#             with self.mux:
#                 return self.spans[:]
#
#     return InMemoryRecorder()
#
#
# # noinspection PyShadowingNames
# @pytest.fixture
# def tracer(span_recorder):
#     return BasicTracer(recorder=span_recorder)
#
#
# @pytest.mark.gen_test
# @pytest.mark.call
# def test_context_should_carry_tracing_info(tracer):
#
#     context = [None, None]
#     server = TChannel(name='server', trace=tracer)
#
#     @server.register(scheme=schemes.RAW)
#     @gen.coroutine
#     def endpoint1(request):
#         yield server.call(  # make recursive call to the 2nd endpoint
#             scheme=schemes.RAW,
#             service='server',
#             arg1='endpoint2',
#             arg2='req headers',
#             arg3='req body',
#             hostport=server.hostport,
#         )
#         context[0] = server.context_provider.get_current_span()
#         raise gen.Return(Response('resp body', 'resp headers'))
#
#     @server.register(scheme=schemes.RAW)
#     def endpoint2(request):
#         context[1] = server.context_provider.get_current_span()
#         return Response('resp body', 'resp headers')
#
#     server.listen()
#
#     # Make a call:
#
#     tchannel = TChannel(name='client', trace=tracer)
#
#     span = tracer.start_span('root-span')
#     span.set_baggage_item('bender', 'is great')
#     with tchannel.context_provider.span_in_context(span):
#         f = tchannel.call(
#             scheme=schemes.RAW,
#             service='server',
#             arg1='endpoint1',
#             arg2='req headers',
#             arg3='req body',
#             hostport=server.hostport,
#         )
#     yield f
#
#     assert context[0].get_baggage_item('bender') == 'is great'
#     assert context[1].get_baggage_item('bender') == 'is great'
