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

import pytest
import threading
from collections import deque, defaultdict
from tornado import gen
from tornado.ioloop import IOLoop

from tchannel._queue import Queue, QueueEmpty


@pytest.fixture
def items():
    return list(range(100))


@pytest.mark.gen_test
def test_put_then_get(items):
    queue = Queue()

    for item in items:
        yield queue.put(item)

    got_futures = []
    for i in range(len(items)):
        got_futures.append(queue.get())

    got = yield got_futures
    assert got == items


@pytest.mark.gen_test
def test_put_then_get_nowait(items):
    queue = Queue()

    for item in items:
        yield queue.put(item)

    got = []
    for i in range(len(items)):
        got.append(queue.get_nowait())

    assert got == items

    with pytest.raises(QueueEmpty):
        queue.get_nowait()

    future = queue.get()
    yield queue.put(42)
    assert 42 == (yield future)


@pytest.mark.gen_test
def test_get_then_put(items):
    queue = Queue()

    got_futures = []
    for i in range(len(items)):
        got_futures.append(queue.get())

    for item in items:
        yield queue.put(item)

    got = yield got_futures
    assert got == items


@pytest.mark.gen_test
@pytest.mark.concurrency_test
def test_concurrent_producers_single_consumer():
    num_threads = 1000
    num_items = 10
    q = Queue()

    def producer(i):

        @gen.coroutine
        def run():
            for j in range(num_items):
                yield q.put((i, j))

        IOLoop(make_current=False).run_sync(run)

    producers = [
        threading.Thread(target=producer, args=(i,))
        for i in range(num_threads)
    ]

    for p in producers:
        p.start()

    items = defaultdict(lambda: [])
    for x in range(num_items * num_threads):
        i, j = yield q.get()
        items[i].append(j)

    for v in items.values():
        assert v == list(range(num_items))

    for p in producers:
        p.join()


@pytest.mark.gen_test
@pytest.mark.concurrency_test
def test_concurrent_consumers_single_producer():
    num_threads = 1000
    num_items = 10

    q = Queue()
    items = deque()

    def consumer():

        @gen.coroutine
        def run():
            for i in range(num_items):
                x = yield q.get()
                items.append(x)

        IOLoop(make_current=False).run_sync(run)

    consumers = [
        threading.Thread(target=consumer) for i in range(num_threads)
    ]

    for c in consumers:
        c.start()

    for x in range(num_items * num_threads):
        yield q.put(x)

    for c in consumers:
        c.join()

    assert len(items) == num_items * num_threads
    assert set(items) == set(range(num_items * num_threads))
    # Order for concurrent consumers cannot be guaranteed because we don't
    # know in which order consumers will wake up. The only guarantee we have
    # is that none of the items were lost.


@pytest.mark.gen_test
@pytest.mark.concurrency_test
def test_concurrent_producers_and_consumers():
    num_threads = 1000
    num_items = 10

    q = Queue()
    items = defaultdict(lambda: [])

    def producer(i):

        @gen.coroutine
        def run():
            for j in range(num_items):
                yield q.put((i, j))

        IOLoop(make_current=False).run_sync(run)

    def consumer():

        @gen.coroutine
        def run():
            for x in range(num_items):
                i, j = yield q.get()
                items[i].append(j)

        IOLoop(make_current=False).run_sync(run)

    num_producers = int(num_threads / 2)
    threads = [
        threading.Thread(target=producer, args=(i,))
        for i in range(num_producers)
    ] + [
        threading.Thread(target=consumer)
        for i in range(num_threads - num_producers)
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    for i in range(num_producers):
        assert len(items[i]) == num_items
        assert set(items[i]) == set(range(num_items))
        # As with the previous concurrent consumers case, we cannot guarantee
        # ordering, only that the items are all present.
