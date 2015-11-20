from __future__ import absolute_import

from .container import heap
from .container.heap import HeapOperation


class PeerHeap(HeapOperation):
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
        n = len(self.peers)
        item = self.peers[n-1]
        item.index = -1
        del self.peers[n - 1]
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
        if len(self.peers) == 0:
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

        if len(self.peers) == 0:
            return None

        return self.peers[0]
