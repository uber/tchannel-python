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

import opentracing_instrumentation


# noinspection PyMethodMayBeStatic
class TracingContextProvider(object):
    """Tracks the OpenTracing Span currently in effect.

    Distributed tracing requires context propagation inside the application,
    do that outbound (downstream) calls can be part of the same trace as the
    inbound request.

    There are two ways to do this:

    * Pass some "context" object to every method that may need to use it.
      This has the best performance but is not always practical.

    * Store the "context" in a thread-local storage, so that it's always
      accessible from anywhere in the application.

    The asynchronous nature of Tornado means that multiple requests can be
    in-flight at any given moment, even in the same thread, so plain thread
    local storage does not work. This class provide an alternative to thread
    local storage by using Tornado's ``StackContext`` functionality.

    There's currently no way to disable Span tracking via ``StackContext``.
    """
    def get_current_span(self):
        """
        :return: The current :py:class:`Span` for this thread.
        """
        return opentracing_instrumentation.get_current_span()

    def span_in_context(self, span):
        """
        Factory method meant to be used as a context manager:

        .. code-block:: python

            with tchannel.context_provider.span_in_context(span):
                handler_fn()

        :param span: an OpenTracing Span
        :return: ``StackContext``-based context manager
        """
        return opentracing_instrumentation.span_in_stack_context(span)
