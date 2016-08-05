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
from tornado.stack_context import StackContext


class TChannelLocal(threading.local):
    __slots__ = ('context',)

    def __init__(self):
        self.context = None

_LOCAL = TChannelLocal()


class RequestContext(object):
    """Tracks the :py:class:`Request` currently being handled.

    .. deprecated:: 0.27.0
        This class is deprecated and not used by TChannel itself.
        It is only kept for backwards compatibility.
        Use tracing.TracingContextProvider

    The asynchronous nature of Tornado means that multiple requests can be
    in-flight at any given moment. It's often useful to be able to see some
    information about the request that triggered the current method invocation.

    There are two ways to do this:

    * Pass the :py:class:`tchannel.Request` to every method that may need to
      use it.  This is performant but breaks MVC boundaries.

    * Use :py:class:`RequestContext` -- in particular
      :py:func:`get_current_context` -- to see this info from any point in your
      code. This can be "easier" (read: magical).

    :py:class:`RequestContext` uses Tornado's ``StackContext`` functionality,
    which hurts throughput. There's currently no way to disable
    :py:class:`RequestContext` tracking (for cases when you want to pass the
    :py:class:`tchannel.Request` explicity), although it is planned.


    :ivar parent_tracing:
        Tracing information (trace id, span id) for this request.
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


# noinspection PyMethodMayBeStatic
class RequestContextProvider(object):
    """
    .. deprecated:: 0.27.0
        This class is deprecated and not used by TChannel itself.
        It is only kept for backwards compatibility.
        Use tracing.TracingContextProvider
    """
    def get_current_context(self):
        """
        :return: The current :py:class:`RequestContext` for this thread.
        """
        return _LOCAL.context

    def request_context(self, parent_tracing):
        """
        Factory method meant to be used as:

        .. code-block:: python

            with tchannel.context_provider.request_context(parent_tracing):
                handler_fn()

        :param parent_tracing:
        :return:
        """
        # TODO should this be using a thread-safe version of StackContext?
        return StackContext(lambda: RequestContext(parent_tracing))
