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

"""
This module implements tombstones for TChannel connections.

A tombstone is a marker for a request that timed out. Often, shortly after a
request times out, we receive a message for it anyway. This is because the
server's timeout is often skewed. So if we immediately forget about the
request on timeout, we'll see an "unconusmed message" error when we receive
these zombie messages. To avoid this, we leave a tombstone behind for the
request that timed out so that we know it is safe to ignore the zombie
messages.

Tombstones are destroyed automatically after a fixed duration.
"""

from __future__ import (
    absolute_import, unicode_literals, print_function, division
)

from tornado.ioloop import IOLoop


# Default offset of time (in seconds) on top of the original request TTL for
# which the tombstone will be active.
DEFAULT_TTL_OFFSET_SECS = 0.5

# Default maximum amount of time (in seconsd) for which a tombstone can be
# active.
DEFAULT_MAX_TTL_SECS = 5


class Cemetery(object):
    """Cemetery is a collection of tombstones.

    A tombstone is just a unique identifier for requests that timed out
    locally.

    :param ttl_offset_secs:
        Amount of time (in seconds) on top of the original request's timeout
        for which the tombstone for that request will exist.
    :param max_ttl_secs:
        Maximum amount of time (in seconds) for which a tombstone for a
        request can exist.
    """

    __slots__ = ('_tombstones', 'io_loop', 'ttl_offset_secs', 'max_ttl_secs')

    def __init__(self, ttl_offset_secs=None, max_ttl_secs=None):
        if ttl_offset_secs is None:
            ttl_offset_secs = DEFAULT_TTL_OFFSET_SECS

        if max_ttl_secs is None:
            max_ttl_secs = DEFAULT_MAX_TTL_SECS

        self._tombstones = {}
        self.ttl_offset_secs = ttl_offset_secs
        self.max_ttl_secs = max_ttl_secs

    def __contains__(self, id):
        """Check if the request with the given id is known to have timed
        out."""
        return id in self._tombstones

    def add(self, id, ttl_secs):
        """Adds a new request to the Cemetery that is known to have timed out.

        The request will be forgotten after ``ttl_secs + ttl_offset_secs``
        seconds.

        :param id:
            ID of the request
        :param ttl_secs:
            TTL of the request (in seconds)
        """
        ttl_secs = min(ttl_secs + self.ttl_offset_secs, self.max_ttl_secs)
        self._tombstones[id] = IOLoop.current().call_later(
            ttl_secs, self.forget, id,
        )

    def forget(self, id):
        """Forget about a specific request."""
        self._tombstones.pop(id, None)

    def clear(self):
        """Forget about all requests."""
        io_loop = IOLoop.current()
        while self._tombstones:
            _, req_timeout = self._tombstones.popitem()
            io_loop.remove_timeout(req_timeout)
