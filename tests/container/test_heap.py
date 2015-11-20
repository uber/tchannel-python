from __future__ import absolute_import
import random
import sys
import math
import pytest
import six

from tchannel.container import heap
from tchannel.container.heap import HeapOperation


class IntHeap(HeapOperation):
    def __init__(self):
        self.values = []

    def size(self):
        return len(self.values)

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

    n = len(values)
    for _ in six.moves.range(n):
        heap.pop(int_heap)
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


@pytest.mark.heapfuzz
@pytest.mark.skipif(True, reason='stress test for the value heap operations')
def test_heap_fuzz(int_heap):
    for _ in six.moves.range(random.randint(1, 100000)):
        ops = random.randint(0, 1)
        if ops == 0:  # push
            heap.push(int_heap, random.randint(0, sys.maxint))
        elif ops == 1:  # pop
            if int_heap.size():
                heap.pop(int_heap)

        if int_heap.size():
            assert smallest(int_heap.values) == int_heap.values[0]

        verify(int_heap, 0)


def smallest(vs):
    m = sys.maxint
    for value in vs:
        if value < m:
            m = value
    return m
