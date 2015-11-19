from __future__ import absolute_import


class HeapOperation(object):
    def cmp(self, i, j):
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


def init(h):
    # heapify
    n = len(h)
    for i in range(n/2 - 1, -1):
        down(h, i, n)


def push(h, x):
    h.push(x)
    up(h, len(h)-1)


def pop(h):
    n = len(h) - 1
    h.swap(0, n)
    down(h, 0, n)
    return h.pop()


def remove(h, i):
    n = len(h) - 1
    if n != i:
        h.swap(i, n)
        down(h, i, n)
        up(h, i)

    return h.pop()


def fix(h, i):
    down(h, i, len(h))
    up(h, i)


def up(h, j):
    while j > 0:
        i = (j - 1) / 2
        if i == j or not h.cmp(j, i):
            break

        h.swap(i, j)
        j = i


def down(h, i, n):
    while True:
        j1 = 2*i + 1
        if j1 >= n or j1 < 0:
            break

        j = j1
        j2 = j1 + 1
        if j2 < n and not h.cmp(j1, j2):
            j = j2

        if not h.cmp(j, i):
            break

        h.swap(i, j)
        i = j
