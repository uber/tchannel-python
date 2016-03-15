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

from __future__ import (
    absolute_import, unicode_literals, division, print_function
)

from collections import deque

from tornado.gen import TimeoutError
from tornado.ioloop import IOLoop
from tornado.queues import QueueEmpty
from tornado.concurrent import Future

__all__ = ['Queue', 'QueueEmpty', 'TimeoutError']


class Queue(object):
    """A specialized version of Tornado's Queue class.

    This class is an almost drop-in replacement for Tornado's Queue class. It
    behaves similar to Tornado's Queue except it provides a ``terminate()``
    function to fail all outstanding operations.

    :param int maxsize:
        If specified, this is the buffer size for the queue. Once the capacity
        is reached, we will start applying backpressure on putters. If
        unspecified or None, the queue is unbuffered.
    """

    __slots__ = ('_getters', '_putters', '_surplus', 'maxsize')

    # How this works:
    #
    # Reads:
    # - Check if we have a value sitting in surplus. If yes, use that.
    #   Otherwise,
    # - Check if we have a putter waiting to provide a value. If yes, use
    #   that. Otherwise,
    # - Store the future in getters for later.
    #
    # Writes:
    # - Check if we have a future waiting for a value in getters. If yes, use
    #   that. Othrewise,
    # - Check if we have room in surplus. If yes, use that. Otherwise,
    # - Store the value and future in putters for later.
    #
    # Invariants:
    # - Either getters is empty or both, surplus and putters are empty.
    # - If putters is non-empty, surplus is maxsize (which is more than 0).

    def __init__(self, maxsize=None):
        if maxsize is None:
            maxsize = 0
        self.maxsize = maxsize

        # collection of futures waiting for values
        self._getters = deque()

        # collection of (value, future) pairs waiting to put values.
        self._putters = deque()

        # collection of values that have not yet been consumed
        self._surplus = deque()

    def terminate(self, exc):
        """Terminate all outstanding get requests with the given exception.

        :param exc:
            An exception or an exc_info triple.
        """
        if isinstance(exc, tuple):
            fail = (lambda f: f.set_exc_info(exc))
        else:
            fail = (lambda f: f.set_exception(exc))

        while self._putters:
            _, future = self._putters.popleft()
            if future.running():
                fail(future)

        while self._getters:
            future = self._getters.popleft()
            if future.running():
                fail(future)

    def __receive_put(self):
        """Receive a value from a waiting putter."""
        while self._putters:
            value, future = self._putters.popleft()
            if future.running():
                self._surplus.append(value)
                future.set_result(None)
                return

    def get(self, timeout=None):
        """Get the next item from the queue.

        Returns a future that resolves to the next item.

        :param timeout:
            If set, the future will resolve to a TimeoutError if a value is
            not received within the given time. The value for ``timeout`` may
            be anything accepted by ``IOLoop.add_timeout`` (a ``timedelta`` or
            an **absolute** time relative to ``IOLoop.time``).
        """
        self.__receive_put()

        answer = Future()
        if self._surplus:
            answer.set_result(self._surplus.popleft())
            return answer

        # Wait for a value
        if timeout is not None:
            _add_timeout(timeout, answer)
        self._getters.append(answer)
        return answer

    def get_nowait(self):
        """Returns a value from the queue without waiting.

        Raises ``QueueEmpty`` if no values are available right now.
        """
        self.__receive_put()

        if self._surplus:
            return self._surplus.popleft()
        raise QueueEmpty()

    def put(self, value, timeout=None):
        """Puts an item into the queue.

        Returns a future that resolves to None once the value has been
        accepted by the queue.

        The value is accepted immediately if there is room in the queue or
        maxsize was not specified.

        :param timeout:
            If set, the future will resolve to a TimeoutError if a value is
            not accepted within the given time. The value for ``timeout`` may
            be anything accepted by ``IOLoop.add_timeout`` (a ``timedelta`` or
            an **absolute** time relative to ``IOLoop.time``).
        """

        answer = Future()

        # If there's a getter waiting, send it the result.
        while self._getters:
            future = self._getters.popleft()
            if future.running():
                future.set_result(value)
                answer.set_result(None)
                return answer

        # We have room. Put the value into surplus.
        if self.maxsize < 1 or len(self._surplus) < self.maxsize:
            self._surplus.append(value)
            answer.set_result(None)
            return answer

        # Wait until there is room.
        if timeout is not None:
            _add_timeout(timeout, answer)
        self._putters.append((value, answer))
        return answer


def _add_timeout(timeout, future):
    io_loop = IOLoop.current()

    def on_timeout():
        if future.running():
            future.set_exception(TimeoutError("timed out"))

    t = io_loop.add_timeout(timeout, on_timeout)
    future.add_done_callback(lambda _: io_loop.remove_timeout(t))
