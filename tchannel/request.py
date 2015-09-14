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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import schemes

__all__ = ['Request']


class Request(object):
    """A TChannel request.

    This is sent by callers and received by registered handlers.

    :ivar body:
        The payload of this request. The type of this attribute depends on the
        scheme being used (e.g., JSON, Thrift, etc.).

    :ivar headers:
        A dictionary of application headers. This should be a mapping of
        strings to strings.

    :ivar transport:
        Protocol-level transport headers. These are used for routing over
        Hyperbahn.

        The most useful piece of information here is probably
        ``request.transport.caller_name``, which is the identity of the
        application that created this request.
    """

    # TODO move over other props from tchannel.tornado.request

    __slots__ = (
        'body',
        'headers',
        'transport',
        'endpoint',
    )

    def __init__(
        self,
        body=None,
        headers=None,
        transport=None,
        endpoint=None,
    ):
        self.body = body
        self.headers = headers
        self.transport = transport
        self.endpoint = endpoint


class TransportHeaders(object):
    """Request Transport Headers"""

    # TODO implement __repr__
    # TODO retry_flags should be woke up past a string

    __slots__ = (
        'caller_name',
        'claim_at_start',
        'claim_at_finish',
        'failure_domain',
        'retry_flags',
        'scheme',
        'speculative_exe',
        'shard_key',
    )

    def __init__(self,
                 caller_name=None,
                 claim_at_start=None,
                 claim_at_finish=None,
                 failure_domain=None,
                 retry_flags=None,
                 scheme=None,
                 speculative_exe=None,
                 shard_key=None,
                 **kwargs):

        if scheme is None:
            scheme = schemes.RAW

        self.caller_name = caller_name
        self.claim_at_start = claim_at_start
        self.claim_at_finish = claim_at_finish
        self.failure_domain = failure_domain
        self.retry_flags = retry_flags
        self.scheme = scheme
        self.speculative_exe = speculative_exe
        self.shard_key = shard_key
