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

import threading
from tornado.stack_context import StackContext


class TChannelLocal(threading.local):
    __slots__ = ('context',)

    def __init__(self):
        self.context = None

_LOCAL = TChannelLocal()


class RequestContext(object):
    """RequestContext is used to save necessary context information related
    to current running async thread.
    """

    __slots__ = ('parent_tracing', '_old_context',)

    def __init__(self, parent_tracing=None):
        self.parent_tracing = parent_tracing
        self._old_context = None

    def __enter__(self):
        self._old_context = _LOCAL.context
        _LOCAL.context = self

    def __exit__(self, type, value, traceback):
        _LOCAL.context = self._old_context


def get_current_context():
    """

    :return: request context in current running aysnc thread.
    """
    return _LOCAL.context


def request_context(parent_tracing):
    return StackContext(lambda: RequestContext(parent_tracing))
