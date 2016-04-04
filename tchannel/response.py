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
from .status import OK

__all__ = ['Response']


class Response(object):
    """A TChannel response.

    This is sent by handlers and received by callers.

    :ivar body:
        The payload of this response. The type of this attribute depends on the
        scheme being used (e.g., JSON, Thrift, etc.).

    :ivar headers:
        A dictionary of application headers. This should be a mapping of
        strings to strings.

    :ivar transport:
        Protocol-level transport headers. These are used for routing over
        Hyperbahn.
    """

    # TODO implement __repr__

    __slots__ = (
        'body',
        'status',
        'headers',
        'transport',
    )

    def __init__(self, body=None, headers=None, transport=None, status=None):
        if status is None:
            status = OK
        self.body = body
        self.status = status
        self.headers = headers
        self.transport = transport


class TransportHeaders(object):
    """Response-specific Transport Headers"""

    # TODO implement __repr__

    __slots__ = (
        'failure_domain',
        'scheme',
    )

    def __init__(self, failure_domain=None, scheme=None):
        if scheme is None:
            scheme = schemes.RAW

        self.failure_domain = failure_domain
        self.scheme = scheme

    @classmethod
    def from_dict(cls, data):
        return cls(
            failure_domain=data.get(t.FAILURE_DOMAIN),
            scheme=data.get(t.SCHEME),
        )

    def to_dict(self):
        m = {}

        if self.failure_domain is not None:
            m[t.FAILURE_DOMAIN] = self.failure_domain

        if self.scheme is not None:
            m[t.SCHEME] = self.scheme

        return m


def response_from_mixed(mixed):
    """Create Response from mixed input."""

    # if none then give empty Response
    if mixed is None:
        return Response()

    # if not Response, then treat like body
    if not isinstance(mixed, Response):
        return Response(mixed)

    # it's already a Response
    return mixed
