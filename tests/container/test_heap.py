from __future__ import absolute_import
import random
import sys
import pytest
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
        n = len(self.values)
        item = self.values[n - 1]
        del self.values[n - 1]
        return item

    def swap(self, i, j):
        self.values[i], self.values[j] = self.values[j], self.values[i]


n = 1000


@pytest.fixture
def int_heap():
    return IntHeap()


def create_values(n):
    values = []
    for i in range(n):
        values.append(i)

    random.shuffle(values)
    return values


def verify(ph, parent):
    child1 = 2 * parent + 1
    child2 = 2 * parent + 2
    if child2 < ph.size():
        assert ph.lt(parent, child1)
        verify(ph, child1)

    if child2 < ph.size():
        assert ph.lt(parent, child2)
        verify(ph, child2)


def test_init(int_heap):
    int_heap.values = create_values(n)
    heap.init(int_heap)
    verify(int_heap, 0)


def test_push(int_heap):
    values = create_values(n)
    for value in values:
        heap.push(int_heap, value)
        verify(int_heap, 0)

    assert int_heap.size() == n


def test_pop(int_heap):
    values = create_values(n)
    for value in values:
        heap.push(int_heap, value)
        verify(int_heap, 0)

    for i in range(n):
        assert i == heap.pop(int_heap)

    assert int_heap.size() == 0


@pytest.mark.heapfuzz
@pytest.mark.skipif(True, reason='stress test for the value heap operations')
def test_heap_fuzz(int_heap):
    for i in range(random.randint(1, 100000)):
        ops = random.randint(0, 1)
        if ops == 0:  # push
            heap.push(int_heap, random.randint(0, sys.maxint))
        elif ops == 1:  # pop
            if int_heap.size():
                heap.pop(int_heap)

        if int_heap.size():
            assert smallest(int_heap.values) == int_heap.values[0]

        verify(int_heap, 0)


def smallest(values):
    m = sys.maxint
    for value in values:
        if value < m:
            m = value
    return m
