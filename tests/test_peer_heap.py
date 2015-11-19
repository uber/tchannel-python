from __future__ import absolute_import
import sys

import mock
import random
import pytest
from tchannel.peer_heap import PeerHeap


n = 1000


@pytest.fixture
def peer_heap():
    return PeerHeap()


def lt(s, o):
    return s.score < o.score


def mock_peer(score=None):
    peer = mock.MagicMock()
    peer.index = -1
    peer.score = score if score is not None else random.randint(0, sys.maxint)
    peer.__lt__ = lt
    return peer


def mock_peers(n):
    peers = []
    for i in range(n):
        peers.append(mock_peer(i))

    random.shuffle(peers)
    return peers


def test_push(peer_heap):
    peers = mock_peers(n)
    for peer in peers:
        peer_heap.push_peer(peer)

    assert len(peer_heap) == n


def test_pop(peer_heap):
    peers = mock_peers(n)
    for peer in peers:
        peer_heap.push_peer(peer)

    for i in range(n):
        assert i == peer_heap.pop_peer().score

    assert len(peer_heap) == 0


def test_update(peer_heap):
    peers = mock_peers(n)
    for peer in peers:
        peer_heap.push_peer(peer)

    p = peer_heap.peers[n-1]
    p.score = -1
    peer_heap.update_peer(p)

    assert peer_heap.peek_peer().score == -1
    assert peer_heap.peek_peer() == p


@pytest.mark.heapfuzz
@pytest.mark.skipif(True, reason='stress test for the peer heap operations')
def test_heap_fuzz(peer_heap):
    for i in range(random.randint(1, 1000000)):
        ops = random.randint(0, 2)
        if ops == 0:    # push
            peer_heap.push_peer(mock_peer())
        elif ops == 1:  # pop
            peer_heap.pop_peer()
        elif ops == 2:  # update
            if len(peer_heap) <= 0:
                continue
            p = peer_heap.peers[random.randint(0, len(peer_heap) - 1)]
            p.score = random.randint(0, sys.maxint)
            peer_heap.update_peer(p)

        if len(peer_heap.peers):
            assert smallest(peer_heap.peers) == peer_heap.peek_peer().score


def smallest(peers):
    m = sys.maxint
    for peer in peers:
        if peer.score < m:
            m = peer.score

    return m