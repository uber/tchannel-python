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

import threading
from collections import namedtuple

from tornado.ioloop import IOLoop
from tornado.queues import QueueEmpty
from tornado.concurrent import Future

__all__ = ['Queue', 'QueueEmpty']


Node = namedtuple('Node', 'value next')


class Queue(object):
    """An unbounded, thread-safe asynchronous queue."""

    __slots__ = ('_get', '_put', '_lock')

    # How this works:
    #
    # _get and _put are futures maintaining pointers to a linked list of
    # futures. The linked list is implemented as Node objects holding the
    # value and the next future.
    #
    #     Node
    #   +---+---+   +---+---+  E: Empty future
    #   | 1 | F-|-->| 2 | E |  F: Filled future
    #   +---+---+   +---+---+
    #         ^           ^
    #   +---+ |     +---+ |
    #   | F-|-+     | F-|-+
    #   +---+       +---+
    #    _get        _put
    #
    # When there's a put, we fill the current empty future with a Node
    # containing the value and a pointer to the next, newly created empty
    # future.
    #
    #   +---+---+   +---+---+   +---+---+
    #   | 1 | F-|-->| 2 | F-|-->| 3 | E |
    #   +---+---+   +---+---+   +---+---+
    #         ^                       ^
    #   +---+ |                 +---+ |
    #   | F-|-+                 | F-|-+
    #   +---+                   +---+
    #    _get                    _put
    #
    # When there's a get, we read the value from the current Node, and move
    # _get to the next future.
    #
    #   +---+---+   +---+---+
    #   | 2 | F-|-->| 3 | E |
    #   +---+---+   +---+---+
    #         ^           ^
    #   +---+ |     +---+ |
    #   | F-|-+     | F-|-+
    #   +---+       +---+
    #    _get        _put

    def __init__(self):
        self._lock = threading.Lock()

        # Space for the next Node.
        hole = Future()

        # Pointer to the Future that will contain the next Node.
        self._get = Future()
        self._get.set_result(hole)

        # Pointer to the next empty Future that should be filled with a Node.
        self._put = Future()
        self._put.set_result(hole)

    def put(self, value):
        """Puts an item into the queue.

        Returns a Future that resolves to None once the value has been
        accepted by the queue.
        """
        io_loop = IOLoop.current()
        new_hole = Future()

        new_put = Future()
        new_put.set_result(new_hole)

        with self._lock:
            self._put, put = new_put, self._put

        answer = Future()

        def _on_put(future):
            if future.exception():  # pragma: no cover (never happens)
                return answer.set_exc_info(future.exc_info())

            old_hole = put.result()
            old_hole.set_result(Node(value, new_hole))
            answer.set_result(None)

        io_loop.add_future(put, _on_put)
        return answer

    def get_nowait(self):
        """Returns a value from the queue without waiting.

        Raises ``QueueEmpty`` if no values are available right now.
        """
        new_get = Future()

        with self._lock:
            if not self._get.done():
                raise QueueEmpty
            get, self._get = self._get, new_get

        hole = get.result()
        if not hole.done():
            # Restore the unfinished hole.
            new_get.set_result(hole)
            raise QueueEmpty

        value, new_hole = hole.result()
        new_get.set_result(new_hole)
        return value

    def get(self):
        """Gets the next item from the queue.

        Returns a Future that resolves to the next item once it is available.
        """
        io_loop = IOLoop.current()
        new_get = Future()

        with self._lock:
            get, self._get = self._get, new_get

        answer = Future()

        def _on_node(future):
            if future.exception():  # pragma: no cover (never happens)
                return answer.set_exc_info(future.exc_info())

            value, new_hole = future.result()
            new_get.set_result(new_hole)
            answer.set_result(value)

        def _on_get(future):
            if future.exception():  # pragma: no cover (never happens)
                return answer.set_exc_info(future.exc_info())

            hole = future.result()
            io_loop.add_future(hole, _on_node)

        io_loop.add_future(get, _on_get)
        return answer
