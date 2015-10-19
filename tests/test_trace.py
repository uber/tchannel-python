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

import pytest

from tchannel import TChannel, schemes
from tchannel.errors import BadRequestError
from tchannel.event import EventHook


@pytest.mark.gen_test
def test_error_trace():
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
            timeout=0.02,
        )

    assert hook.error_trace
    assert hook.request_trace
    assert hook.error_trace == hook.request_trace
