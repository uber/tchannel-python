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
from __future__ import division

import math
import six
from collections import deque


class NoMatchError(Exception):
    pass


class HeapOperation(object):
    """HeapOperation defines the interface on how to manipulate the heap.
    Any extension of heap class should implement all the heap operations in
    order to have complete heap functions.
    """

    def lt(self, i, j):
        """Compare the items in position i and j of the heap.

        :param i: the first item's position of the heap list
        :param j: the second item's position of the heap list
        :return true if items[i] < items[j], otherwise false.
        """
        raise NotImplementedError()

    def push(self, x):
        """Push a new item into heap"""
        raise NotImplementedError()

    def pop(self):
        """Pop an item from the heap"""
        raise NotImplementedError()

    def peek(self, i):
        """Peek at the item at the given position without removing it from the
        heap.

        :param i:
            0-indexed position of the iteam in the heap
        """
        raise NotImplementedError()

    def swap(self, i, j):
        """swap items between position i and j of the heap"""
        raise NotImplementedError()

    def size(self):
        """Return length of the heap."""
        raise NotImplementedError()


def init(h):
    """Initialize existing object into the heap."""
    # heapify
    n = h.size()
    for i in six.moves.range(int(math.floor(n/2)) - 1, -1, -1):
        down(h, i, n)


def push(h, x):
    """Push a new value into heap."""
    h.push(x)
    up(h, h.size()-1)


def pop(h):
    """Pop the heap value from the heap."""
    n = h.size() - 1
    h.swap(0, n)
    down(h, 0, n)
    return h.pop()


def remove(h, i):
    """Remove the item at position i of the heap."""
    n = h.size() - 1
    if n != i:
        h.swap(i, n)
        down(h, i, n)
        up(h, i)

    return h.pop()


def fix(h, i):
    """Rearrange the heap after the item at position i got updated."""
    down(h, i, h.size())
    up(h, i)


def up(h, child):
    while child > 0:
        parent = int(math.floor((child - 1) / 2))
        if not h.lt(child, parent):
            break

        h.swap(parent, child)
        child = parent


def down(h, parent, n):
    while True:
        child1 = 2 * parent + 1
        if child1 >= n or child1 < 0:
            break

        min_child = child1
        child2 = child1 + 1
        if child2 < n and not h.lt(child1, child2):
            min_child = child2

        if not h.lt(min_child, parent):
            break

        h.swap(parent, min_child)
        parent = min_child


def smallest(heap, predicate):
    """Finds the index of the smallest item in the heap that matches the given
    predicate.

    :param heap:
        Heap on which this search is being performed.
    :param predicate:
        Function that accepts an item from the heap and returns true or false.
    :returns:
        Index of the first item for which ``predicate`` returned true.
    :raises NoMatchError:
        If no matching items were found.
    """
    n = heap.size()

    # items contains indexes of items yet to be checked.
    items = deque([0])
    while items:
        current = items.popleft()
        if current >= n:
            continue

        if predicate(heap.peek(current)):
            return current

        child1 = 2 * current + 1
        child2 = child1 + 1

        if child1 < n and child2 < n and heap.lt(child2, child1):
            # make sure we check the smaller child first.
            child1, child2 = child2, child1

        if child1 < n:
            items.append(child1)

        if child2 < n:
            items.append(child2)

    raise NoMatchError()
