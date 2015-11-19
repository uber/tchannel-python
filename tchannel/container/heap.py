from __future__ import absolute_import
from __future__ import division

import math
import six


class HeapOperation(object):
    """HeapOperation defines the interface on how to manipulate the heap.
    Any extension of heap class should implement all the heap operations in
    order to have complete heap functions.
    """

    def less(self, i, j):
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

    def swap(self, i, j):
        """swap items between position i and j of the heap"""
        raise NotImplementedError()

    def size(self):
        """Return length of the heap."""
        raise NotImplementedError()


def init(h):
    # heapify
    n = h.size()
    for i in six.moves.range(int(math.floor(n/2)) - 1, -1):
        down(h, i, n)


def push(h, x):
    h.push(x)
    up(h, h.size()-1)


def pop(h):
    n = h.size() - 1
    h.swap(0, n)
    down(h, 0, n)
    return h.pop()


def remove(h, i):
    n = h.size() - 1
    if n != i:
        h.swap(i, n)
        down(h, i, n)
        up(h, i)

    return h.pop()


def fix(h, i):
    down(h, i, h.size())
    up(h, i)


def up(h, child):
    while child > 0:
        parent = int(math.floor((child - 1) / 2))
        if not h.less(child, parent):
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
        if child2 < n and not h.less(child1, child2):
            min_child = child2

        if not h.less(min_child, parent):
            break

        h.swap(parent, min_child)
        parent = min_child
