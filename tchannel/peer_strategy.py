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

import sys


class RankCalculator(object):
    """RankCalculator calculates the rank of a peer."""

    def get_rank(self, peer):
        raise NotImplementedError()


class PreferIncomingCalculator(RankCalculator):

    # TIERS lists three ranges for three different kinds of peers.
    # 0: ephemeral peers or unconnected peers
    # 1: peers with only outgoing connections
    # 2: peers with incoming connections
    TIERS = [sys.maxint, sys.maxint / 2, 0]

    def get_rank(self, peer):
        """Calculate the peer rank based on connections.

        If the peer has no incoming connections, it will have largest rank.
        In our peer selection strategy, the largest number has least priority
        in the heap.

        If the peer has incoming connections, we will return number of outbound
        pending requests and responses.

        :param peer: instance of `tchannel.tornado.peer.Peer`
        :return: rank of the peer
        """
        if not peer.connections:
            return self.TIERS[0]

        if not peer.has_incoming_connections:
            return self.TIERS[1] + peer.total_outbound_pendings

        return self.TIERS[2] + peer.total_outbound_pendings
