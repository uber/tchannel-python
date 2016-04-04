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

from .container import heap
from .container.heap import HeapOperation
from .container.heap import NoMatchError
from .container.heap import smallest


class PeerHeap(HeapOperation):
    """PeerHeap maintains a min-heap of peers based on their ranks.

    Peer in the heap will be arranged based on the peer's rank and peer's
    order. Order is equal to peer heap's current order number plus random value
    within the current peer size. It solves two problems when peers are in
    same rank:

    Dead peers: If the order is completely random, then an unlucky peer
    with a very bad assigned order may never get selected.

    Determinism: If the insertion order is used as-is, then all TChannel
    instances would follow the same selection pattern, causing load
    imbalance. For example if they get the same static list of peers, they
    will all pick the first one, then the second one, and so on, cycling
    between which host gets overloaded with requests.

    All in all, it will keep certain level randomization but at the same
    time make the peer rank not deterministic among different tchannel
    instances.

    """

    __slots__ = ('peers',)

    def __init__(self):
        self.peers = []
        self.order = 0

    def size(self):
        return len(self.peers)

    def lt(self, i, j):
        """Compare the priority of two peers.

        Primary comparator will be the rank of each peer. If the ``rank`` is
        same then compare the ``order``. The ``order`` attribute of the peer
        tracks the heap push order of the peer. This help solve the imbalance
        problem caused by randomization when deal with same rank situation.

        :param i: ith peer
        :param j: jth peer
        :return: True or False
        """
        if self.peers[i].rank == self.peers[j].rank:
            return self.peers[i].order < self.peers[j].order

        return self.peers[i].rank < self.peers[j].rank

    def peek(self, i):
        return self.peers[i]

    def push(self, x):
        x.index = len(self.peers)
        self.peers.append(x)

    def pop(self):
        item = self.peers.pop()
        return item

    def swap(self, i, j):
        self.peers[i], self.peers[j] = self.peers[j], self.peers[i]
        self.peers[i].index = i
        self.peers[j].index = j

    def update_peer(self, peer):
        """Update the peer's position in the heap after peer's rank changed"""
        heap.fix(self, peer.index)

    def pop_peer(self):
        """Pop the top peer from the heap

        :return
            return the top peer and remove it from the heap if heap is not
            empty.Otherwise return None.
        """
        if not self.peers:
            return None
        return heap.pop(self)

    def push_peer(self, peer):
        """Push a new peer into the heap"""

        self.order += 1
        peer.order = self.order + random.randint(0, self.size())
        heap.push(self, peer)

    def add_and_shuffle(self, peer):
        """Push a new peer into the heap and shuffle the heap"""
        self.push_peer(peer)

        r = random.randint(0, self.size() - 1)
        self.swap_order(peer.index, r)

    def peek_peer(self):
        """Return the top peer of the heap
        :return
            return the top peer if heap is not empty. Otherwise return None.
        """

        if not self.peers:
            return None

        return self.peers[0]

    def remove_peer(self, peer):
        """Remove the peer from the heap.

        Return: removed peer if peer exists. If peer's index is out of range,
        raise IndexError.
        """
        if peer.index < 0 or peer.index >= self.size():
            raise IndexError('Peer index is out of range')

        assert peer is self.peers[peer.index], "peer is not in the heap"

        return heap.remove(self, peer.index)

    def smallest_peer(self, predicate):
        """Return the smallest peer in the heap that matches the given
        predicate.

        :param predicate:
            Function that accepts an item from the heap and returns
            true or false.
        :returns:
            The first peer for which ``predicate`` returned true.
        """
        try:
            return self.peek(
                smallest(self, predicate),
            )
        except NoMatchError:
            return None

    def swap_order(self, index1, index2):
        if index1 == index2:
            return

        p1 = self.peers[index1]
        p2 = self.peers[index2]

        (p1.order, p2.order) = (p2.order, p1.order)

        heap.fix(self, p1.index)
        heap.fix(self, p2.index)
