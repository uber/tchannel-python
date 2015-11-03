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

from __future__ import absolute_import
import mock

from tchannel.messages.call_request_continue import CallRequestContinueMessage
from tchannel.messages.call_request import CallRequestMessage
from tchannel.serializer.raw import RawSerializer
from tchannel.tornado.dispatch import RequestDispatcher


def dummy_endpoint(request, response):
    pass


def test_dispatch():
    dispatcher = RequestDispatcher()

    dispatcher.register(
        r"/hello",
        dummy_endpoint,
        RawSerializer(),
        RawSerializer(),
    )

    endpoint = dispatcher.handlers.get("/hello")[0]
    assert endpoint == dummy_endpoint


def test_dispatch_call_req():
    with mock.patch(
        "tchannel.tornado.dispatch.RequestDispatcher.handle_call_req",
        autospec=True,
    ) as mock_call_req:
        with mock.patch.dict(
            RequestDispatcher._HANDLERS,
            {CallRequestMessage.message_type: mock_call_req},
            clear=True,
        ):
            dispatcher = RequestDispatcher()
            callReq = CallRequestMessage()
            dispatcher.handle(callReq, None)
            mock_call_req.assert_called_with(mock.ANY, callReq, None)


def test_dispatch_call_req_cont():
    with mock.patch(
        "tchannel.tornado.dispatch.RequestDispatcher.handle_call_req_cont",
        autospec=True,
    ) as mock_call_req_cont:
        with mock.patch.dict(
            RequestDispatcher._HANDLERS,
            {CallRequestContinueMessage.message_type: mock_call_req_cont},
            clear=True,
        ):
            dispatcher = RequestDispatcher()
            callReqCont = CallRequestContinueMessage()
            dispatcher.handle(callReqCont, None)
            mock_call_req_cont.assert_called_with(mock.ANY, callReqCont, None)
