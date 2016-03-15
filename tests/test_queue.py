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

import sys
import pytest
from datetime import timedelta
from six.moves import range
from tornado import gen

from tchannel._queue import Queue, QueueEmpty, TimeoutError


def assert_invariant(q):
    assert not (q._getters and (q._surplus or q._putters))
    assert (not q._putters or len(q._surplus) == q.maxsize)


@pytest.fixture
def items():
    return list(range(100))


@pytest.mark.gen_test
def test_unbounded_put_then_get(items):
    queue = Queue()
    assert_invariant(queue)

    for item in items:
        yield queue.put(item)
        assert_invariant(queue)

    got_futures = []
    for i in range(len(items)):
        got_futures.append(queue.get())
        assert_invariant(queue)

    got = yield got_futures
    assert got == items

    with pytest.raises(TimeoutError):
        yield queue.get(timedelta(seconds=0.1))


@pytest.mark.gen_test
def test_bounded_put_then_get(items):
    queue = Queue(5)
    assert_invariant(queue)

    for item in items[:5]:
        yield queue.put(item)
        assert_invariant(queue)

    put_futures = []
    for item in items[5:]:
        put_futures.append(queue.put(item))

    got = []
    for i in range(len(items)):
        item = yield queue.get()
        assert_invariant(queue)
        got.append(item)

    assert got == items
    yield put_futures


@pytest.mark.gen_test
def test_bounded_put_timeout_then_get(items):
    queue = Queue(1)
    assert_invariant(queue)

    yield queue.put(items[0])

    put_futures = []
    for item in range(len(items)):
        put_futures.append(queue.put(item, timedelta(seconds=0.001)))

    yield gen.sleep(0.01)

    get_futures = []
    for item in range(len(items)):
        get_futures.append(queue.get())

    for future in put_futures:
        with pytest.raises(TimeoutError):
            yield future

    for item in items[1:]:
        yield queue.put(item)

    got = yield get_futures
    assert got == items


@pytest.mark.gen_test
def test_unbounded_put_then_get_nowait(items):
    queue = Queue()

    for item in items:
        yield queue.put(item)
        assert_invariant(queue)

    got = []
    for i in range(len(items)):
        got.append(queue.get_nowait())
        assert_invariant(queue)

    assert got == items

    with pytest.raises(QueueEmpty):
        queue.get_nowait()


@pytest.mark.gen_test
def test_unbounded_get_then_put(items):
    queue = Queue()

    got_futures = []
    for i in range(len(items)):
        got_futures.append(queue.get())
        assert_invariant(queue)

    for item in items:
        yield queue.put(item)
        assert_invariant(queue)

    got = yield got_futures
    assert got == items


@pytest.mark.gen_test
def test_unbounded_expired_gets_then_get_first():
    queue = Queue()

    expired_gets = []
    for i in range(99):
        expired_gets.append(queue.get(timedelta(seconds=0.001)))
        assert_invariant(queue)

    yield gen.sleep(0.01)  # 99 * 0.001 = 0.099

    # get the value before putting it
    real_get = queue.get()
    yield queue.put(42)
    assert 42 == (yield real_get)
    assert_invariant(queue)

    for future in expired_gets:
        with pytest.raises(TimeoutError):
            yield future


@pytest.mark.gen_test
def test_unbounded_expired_gets_then_put_first():
    queue = Queue()

    expired_gets = []
    for i in range(99):
        expired_gets.append(queue.get(timedelta(seconds=0.001)))
        assert_invariant(queue)

    yield gen.sleep(0.01)

    # put the value first, get afterwards
    yield queue.put(42)
    assert 42 == (yield queue.get())
    assert_invariant(queue)

    for future in expired_gets:
        with pytest.raises(TimeoutError):
            yield future


@pytest.mark.gen_test
def test_terminate_get_with_exception():

    class GreatSadness(Exception):
        pass

    queue = Queue()
    expired_gets = []
    terminated_gets = []

    flag = True
    for i in range(99):
        if flag:
            expired_gets.append(queue.get(timedelta(seconds=0.001)))
        else:
            terminated_gets.append(queue.get(timedelta(seconds=1)))
        flag = not flag

    yield gen.sleep(0.01)

    queue.terminate(GreatSadness())

    for future in expired_gets:
        with pytest.raises(TimeoutError):
            yield future

    for future in terminated_gets:
        with pytest.raises(GreatSadness):
            yield future


@pytest.mark.gen_test
def test_terminate_put_with_exception():

    class GreatSadness(Exception):
        pass

    queue = Queue(10)
    expired_puts = []
    terminated_puts = []

    for i in range(10):
        yield queue.put(i)

    flag = True
    for i in range(99):
        if flag:
            expired_puts.append(queue.put(i, timedelta(seconds=0.001)))
        else:
            terminated_puts.append(queue.put(i, timedelta(seconds=1)))
        flag = not flag

    yield gen.sleep(0.01)

    try:
        raise GreatSadness()
    except GreatSadness:
        queue.terminate(sys.exc_info())
    else:
        assert False, "expected failure"

    for future in expired_puts:
        with pytest.raises(TimeoutError):
            yield future

    for future in terminated_puts:
        with pytest.raises(GreatSadness):
            yield future


@pytest.mark.gen_test
def test_get_timeout_too_late():
    queue = Queue()
    future = queue.get(timedelta(seconds=0.01))
    yield queue.put(42)
    yield gen.sleep(0.01)
    assert 42 == (yield future)


@pytest.mark.gen_test
def test_put_timeout_too_late():
    queue = Queue(1)
    yield queue.put(1)
    future = queue.put(2, timedelta(seconds=0.01))
    assert (yield queue.get()) == 1
    assert (yield queue.get()) == 2
    yield gen.sleep(0.01)
    yield future
