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


class ZipkinTraceHook(EventHook):
    """
    .. deprecated:: 0.27.0
        Deprecated no-op hook kept only for backwards compatibility.
    """

    DEFAULT_RATE = 0.01

    def __init__(self, tchannel=None, dst=None, sample_rate=None):
        pass

    def before_send_request(self, request):
        pass

    def before_receive_request(self, request):
        pass

    def after_send_response(self, response):
        pass

    def after_receive_response(self, request, response):
        pass

    def after_receive_error(self, request, error):
        pass

    def after_send_error(self, error):
        pass
