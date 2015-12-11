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

from __future__ import absolute_import

import random

from .container import heap
from .container.heap import HeapOperation


class PeerHeap(HeapOperation):
    """PeerHeap maintains a min-heap of peers based on their scores."""

    __slots__ = ('peers',)

    def __init__(self):
        self.peers = []
        self.order = 0

    def size(self):
        return len(self.peers)

    def lt(self, i, j):
        """Compare the priority of two peers.

        Primary comparator will be the score of each peer. If the ``score`` is
        same then compare the ``order``. The ``order`` attribute of the peer
        tracks the heap push order of the peer. This help solve the imbalance
        problem caused by randomization when deal with same score situation.

        :param i: ith peer
        :param j: jth peer
        :return: True or False
        """
        if self.peers[i].score == self.peers[j].score:
            return self.peers[i].order < self.peers[j].order

        return self.peers[i].score < self.peers[j].score

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
        """Update the peer's position in the heap after peer's score changed"""
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
        """Push a new peer into the heap

        Order is equal to peer heap's current order plus random value within
        the current peer size. It solves two problems when peers are in
        same score:

        1. 'dead peer' caused by random problem. If use fully random value, and
        one peer is very unlock to get the worst value, as the peer selection
        keeps working, that peer may not be selected anymore.

        2. deterministic problem. If we just use push order, then all the
        tchannel instance will follow the same pattern. If they all get the
        same list of hyperbahn nodes, the peers that they pick to talk to
        hyperbahn will be same. In that situation, it will cause the hyperbahn
        node received very imbalance requests from tchannel clients.

        All in all, it will keep certain level randomization but at the same
        time make the peer score not deterministic among different tchannel
        instance. For
        """
        self.order += 1
        peer.order = self.order + random.randint(0, self.size())
        heap.push(self, peer)

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
