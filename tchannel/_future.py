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

from __future__ import (
    absolute_import, unicode_literals, division, print_function
)

import sys
from functools import wraps

from tornado.gen import is_future


def fail_to(future):
    """A decorator for function callbacks to catch uncaught non-async
    exceptions and forward them to the given future.

    The primary use for this is to catch exceptions in async callbacks and
    propagate them to futures. For example, consider,

    .. code-block:: python

        answer = Future()

        def on_done(future):
            foo = bar()
            answer.set_result(foo)

        some_async_operation().add_done_callback(on_done)

    If ``bar()`` fails, ``answer`` will never get filled with an exception or
    a result. Now if we change ``on_done`` to,

    .. code-block:: python

        @fail_to(answer)
        def on_done(future):
            foo = bar()
            answer.set_result(foo)

    Uncaught exceptions in ``on_done`` will be caught and propagated to
    ``answer``. Note that ``on_done`` will return None if an exception was
    caught.

    :param answer:
        Future to which the result will be written.
    """
    assert is_future(future), 'you forgot to pass a future'

    def decorator(f):

        @wraps(f)
        def new_f(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception:
                future.set_exc_info(sys.exc_info())

        return new_f

    return decorator
