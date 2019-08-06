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
import random
import sys
import math
import pytest
import six
from hypothesis import given
from hypothesis import strategies as st

from tchannel.container import heap
from tchannel.container.heap import HeapOperation, NoMatchError


class IntHeap(HeapOperation):
    def __init__(self):
        self.values = []

    def size(self):
        return len(self.values)

    def peek(self, i):
        return self.values[i]

    def lt(self, i, j):
        return self.values[i] < self.values[j]

    def push(self, x):
        self.values.append(x)

    def pop(self):
        return self.values.pop()

    def swap(self, i, j):
        self.values[i], self.values[j] = self.values[j], self.values[i]


@pytest.fixture
def int_heap():
    return IntHeap()


@pytest.fixture(params=['unique', 'duplicate', 'reverse'])
def values(request):
    n = 1000
    v = []

    if request.param == "unique":
        for i in six.moves.range(n):
            v.append(i)
        random.shuffle(v)
    elif request.param == "duplicate":
        for _ in six.moves.range(n):
            v.append(random.randint(0, math.floor(n/20)))
    elif request.param == "reverse":
        for i in six.moves.range(n, -1, -1):
            v.append(i)

    return v


def verify(ph, parent):
    child1 = 2 * parent + 1
    child2 = 2 * parent + 2
    if child2 < ph.size():
        assert not ph.lt(child1, parent)
        verify(ph, child1)

    if child2 < ph.size():
        assert not ph.lt(child2, parent)
        verify(ph, child2)


def test_init(int_heap, values):
    int_heap.values = values
    heap.init(int_heap)
    verify(int_heap, 0)


def test_push(int_heap, values):
    for value in values:
        heap.push(int_heap, value)
        verify(int_heap, 0)

    assert int_heap.size() == len(values)


def test_pop(int_heap, values):
    for value in values:
        heap.push(int_heap, value)
        verify(int_heap, 0)

    for i in sorted(values):
        assert i == heap.pop(int_heap)
        verify(int_heap, 0)

    assert int_heap.size() == 0


def test_remove(int_heap, values):
    for value in values:
        heap.push(int_heap, value)
        verify(int_heap, 0)

    # random remove item from the heap
    n = len(values)
    for i in six.moves.range(n - 1, -1, -1):
        heap.remove(int_heap, random.randint(0, i))
        verify(int_heap, 0)


def test_smallest_basic(int_heap, values):
    for value in values:
        heap.push(int_heap, value)
        verify(int_heap, 0)

    assert heap.smallest(int_heap, (lambda _: True)) == 0

    with pytest.raises(NoMatchError):
        heap.smallest(int_heap, (lambda _: False))


def test_smallest_empty(int_heap):
    with pytest.raises(NoMatchError):
        heap.smallest(int_heap, (lambda _: True))


def test_smallest_unordered_children(int_heap):
    int_heap.values = [1, 4, 2]
    verify(int_heap, 0)

    assert heap.smallest(int_heap, (lambda x: x % 2 == 0)) == 2


@given(st.lists(st.integers(), min_size=1))
def test_smallest_random(values):
    int_heap = IntHeap()
    for v in values:
        heap.push(int_heap, v)

    target = random.choice(int_heap.values)
    valid = [i for (i, v) in enumerate(int_heap.values) if v == target]
    assert heap.smallest(int_heap, (lambda x: x == target)) in valid


@pytest.mark.heapfuzz
@pytest.mark.skipif(True, reason='stress test for the value heap operations')
def test_heap_fuzz(int_heap):
    for _ in six.moves.range(random.randint(1, 100000)):
        ops = random.randint(0, 1)
        if ops == 0:  # push
            heap.push(int_heap, random.randint(0, sys.maxsize))
        elif ops == 1:  # pop
            if int_heap.size():
                heap.pop(int_heap)

        if int_heap.size():
            assert smallest(int_heap.values) == int_heap.values[0]

        verify(int_heap, 0)


def smallest(vs):
    m = sys.maxsize
    for value in vs:
        if value < m:
            m = value
    return m
