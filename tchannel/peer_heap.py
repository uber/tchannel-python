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

from .container import heap
from .container.heap import HeapOperation


class PeerHeap(HeapOperation):
    """PeerHeap maintains a min-heap of peers based on their scores."""

    __slots__ = ('peers',)

    def __init__(self):
        self.peers = []

    def size(self):
        return len(self.peers)

    def lt(self, i, j):
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
        """Push a new peer into the heap"""
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
        Note: Unknown peers are ignored.
        """
        if 0 <= peer.index < self.size():
            p = heap.remove(self, peer.index)
            assert p is peer
