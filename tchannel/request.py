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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import schemes
from . import transport as t

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

    :ivar service:
        Name of the service being called. Inside request handlers, this is
        usually the name of "this" service itself. However, for services that
        simply forward requests to other services, this is the name of the
        target service.

    :ivar timeout:
        Amount of time (in seconds) within which this request is expected to
        finish.
    """

    # TODO move over other props from tchannel.tornado.request

    __slots__ = (
        'body',
        'headers',
        'service',
        'transport',
        'endpoint',
        'timeout',
    )

    def __init__(
        self,
        body=None,
        headers=None,
        transport=None,
        endpoint=None,
        service=None,
        timeout=None,
    ):
        self.body = body
        self.headers = headers
        self.transport = transport
        self.endpoint = endpoint
        self.service = service
        self.timeout = timeout


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
        'routing_delegate',
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
                 routing_delegate=None):

        if scheme is None:
            scheme = schemes.RAW

        self.caller_name = caller_name
        self.claim_at_start = claim_at_start
        self.claim_at_finish = claim_at_finish
        self.failure_domain = failure_domain
        self.retry_flags = retry_flags
        self.routing_delegate = routing_delegate
        self.scheme = scheme
        self.speculative_exe = speculative_exe
        self.shard_key = shard_key

    @classmethod
    def from_dict(cls, data):
        return cls(
            caller_name=data.get(t.CALLER_NAME),
            claim_at_finish=data.get(t.CLAIM_AT_FINISH),
            claim_at_start=data.get(t.CLAIM_AT_START),
            failure_domain=data.get(t.FAILURE_DOMAIN),
            retry_flags=data.get(t.RETRY_FLAGS),
            routing_delegate=data.get(t.ROUTING_DELEGATE),
            scheme=data.get(t.SCHEME),
            shard_key=data.get(t.SHARD_KEY),
            speculative_exe=data.get(t.SPECULATIVE_EXE),
        )

    def to_dict(self):
        m = {}

        if self.caller_name is not None:
            m[t.CALLER_NAME] = self.caller_name

        if self.claim_at_start is not None:
            m[t.CLAIM_AT_START] = self.claim_at_start

        if self.claim_at_finish is not None:
            m[t.CLAIM_AT_FINISH] = self.claim_at_finish

        if self.failure_domain is not None:
            m[t.FAILURE_DOMAIN] = self.failure_domain

        if self.retry_flags is not None:
            m[t.RETRY_FLAGS] = self.retry_flags

        if self.routing_delegate is not None:
            m[t.ROUTING_DELEGATE] = self.routing_delegate

        if self.scheme is not None:
            m[t.SCHEME] = self.scheme

        if self.shard_key is not None:
            m[t.SHARD_KEY] = self.shard_key

        if self.speculative_exe is not None:
            m[t.SPECULATIVE_EXE] = self.speculative_exe

        return m
