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


class ScoreCalculator(object):
    """ScoreCalculator provides interface to calculate the score of a peer."""
    def get_score(self, peer):
        raise NotImplementedError()


class ZeroScoreCalculator(ScoreCalculator):
    def get_score(self, peer):
        return 0


class PreferIncomingCalculator(ScoreCalculator):
    TIERS = [sys.maxint, sys.maxint / 2, 0]

    def get_score(self, peer):
        """Calculate the peer score based on connections.

        If the peer has no incoming connections, it will have largest score.
        In our peer selection strategy, the largest number has least priority
        in the heap.

        If the peer has incoming connections, we will return number of outbound
        pending requests and responses.

        :param peer: instance of `tchannel.tornado.peer.Peer`
        :return: score of the peer
        """
        if peer.is_ephemeral or not peer.connections:
            return self.TIERS[0]

        if not peer.incoming_connections:
            return self.TIERS[1] + peer.total_outbound_pendings

        return self.TIERS[2] + peer.total_outbound_pendings
