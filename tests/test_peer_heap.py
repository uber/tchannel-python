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
import sys
import math

import mock
import random
import pytest
import six
from tchannel.peer_heap import PeerHeap


@pytest.fixture
def peer_heap():
    return PeerHeap()


@pytest.fixture(params=['unique', 'duplicate', 'reverse'])
def peers(request):
    n = 100
    v = []

    if request.param == "unique":
        for i in six.moves.range(n):
            v.append(mock_peer(i))
        random.shuffle(v)
    elif request.param == "duplicate":
        for _ in six.moves.range(n):
            v.append(mock_peer(random.randint(0, math.floor(n/20))))
    elif request.param == "reverse":
        for i in six.moves.range(n, -1, -1):
            v.append(mock_peer(i))

    return v


def mock_peer(rank=None):
    peer = mock.MagicMock()
    peer.index = -1
    peer.rank = rank if rank is not None else random.randint(0, sys.maxint)
    return peer


def verify(ph, parent):
    """Assert the peer is still well-maintained."""
    child1 = 2*parent + 1
    child2 = 2*parent + 2
    if child2 < ph.size():
        assert not ph.lt(child1, parent)
        verify(ph, child1)

    if child2 < ph.size():
        assert not ph.lt(child2, parent)
        verify(ph, child2)


def test_push(peer_heap, peers):
    for peer in peers:
        peer_heap.push_peer(peer)
        verify(peer_heap, 0)

    assert peer_heap.size() == len(peers)


def test_pop(peer_heap, peers):
    for peer in peers:
        peer_heap.push_peer(peer)
        verify(peer_heap, 0)

    n = len(peers)
    for _ in six.moves.range(n):
        peer_heap.pop_peer()
        verify(peer_heap, 0)

    assert peer_heap.size() == 0


def test_update(peer_heap, peers):
    for peer in peers:
        peer_heap.push_peer(peer)
        verify(peer_heap, 0)

    p = peer_heap.peers[len(peers) - 1]
    p.rank = -1
    peer_heap.update_peer(p)
    verify(peer_heap, 0)
    assert peer_heap.peek_peer().rank == -1
    assert peer_heap.peek_peer() == p


def test_remove(peer_heap, peers):
    for peer in peers:
        peer_heap.push_peer(peer)
        verify(peer_heap, 0)

    n = len(peers)
    for _ in six.moves.range(n):
        p = peer_heap.peers[random.randint(0, peer_heap.size() - 1)]
        assert p is peer_heap.remove_peer(p)
        verify(peer_heap, 0)
        verify_peer_not_in_heap(peer_heap, p)


def verify_peer_not_in_heap(peer_heap, p):
    for peer in peer_heap.peers:
        assert peer is not p


def test_remove_duplicate(peer_heap, peers):
    for peer in peers:
        peer_heap.push_peer(peer)
        verify(peer_heap, 0)

    n = random.randint(0, len(peers))

    for _ in six.moves.range(n):
        p = peer_heap.peers[random.randint(0, peer_heap.size() - 1)]
        assert p is peer_heap.remove_peer(p)
        with pytest.raises(IndexError):
            peer_heap.remove_peer(p)
        verify(peer_heap, 0)
        verify_peer_not_in_heap(peer_heap, p)


def test_remove_from_empty_heap():
    heap = PeerHeap()
    with pytest.raises(IndexError):
        heap.remove_peer(mock_peer())


def test_remove_mismatch(peer_heap, peers):
    for peer in peers:
        peer_heap.push_peer(peer)
        verify(peer_heap, 0)

    # create a fake peer with duplicated index.
    fake_peer = mock_peer()
    fake_peer.index = 1
    with pytest.raises(AssertionError) as e:
        peer_heap.remove_peer(fake_peer)

    assert e.value.message == 'peer is not in the heap'


@pytest.mark.heapfuzz
@pytest.mark.skipif(True, reason='stress test for the peer heap operations')
def test_heap_fuzz(peer_heap):
    for _ in six.moves.range(random.randint(1, 100000)):
        ops = random.randint(0, 2)
        if ops == 0:    # push
            peer_heap.push_peer(mock_peer())
        elif ops == 1:  # pop
            peer_heap.pop_peer()
        elif ops == 2:  # update
            if len(peer_heap) <= 0:
                continue
            p = peer_heap.peers[random.randint(0, len(peer_heap) - 1)]
            p.rank = random.randint(0, sys.maxint)
            peer_heap.update_peer(p)

        if peer_heap.size():
            assert smallest(peer_heap.peers) == peer_heap.peek_peer().rank

        verify(peer_heap, 0)


def smallest(ps):
    m = sys.maxint
    for peer in ps:
        if peer.rank < m:
            m = peer.rank

    return m
