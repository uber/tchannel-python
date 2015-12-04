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


def mock_peer(score=None):
    peer = mock.MagicMock()
    peer.index = -1
    peer.score = score if score is not None else random.randint(0, sys.maxint)
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
    p.score = -1
    peer_heap.update_peer(p)
    verify(peer_heap, 0)
    assert peer_heap.peek_peer().score == -1
    assert peer_heap.peek_peer() == p


def test_remove(peer_heap, peers):
    for peer in peers:
        peer_heap.push_peer(peer)
        verify(peer_heap, 0)

    n = len(peers)
    for _ in six.moves.range(n):
        p = peer_heap.peers[random.randint(0, peer_heap.size() - 1)]
        peer_heap.remove_peer(p)
        verify(peer_heap, 0)


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
            p.score = random.randint(0, sys.maxint)
            peer_heap.update_peer(p)

        if peer_heap.size():
            assert smallest(peer_heap.peers) == peer_heap.peek_peer().score

        verify(peer_heap, 0)


def smallest(ps):
    m = sys.maxint
    for peer in ps:
        if peer.score < m:
            m = peer.score

    return m