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

__all__ = ['Response']


class Response(object):
    """TChannel Response"""

    # TODO implement __repr__

    __slots__ = (
        'body',
        'headers',
        'transport',
    )

    def __init__(self, body=None, headers=None, transport=None):
        self.body = body
        self.headers = headers
        self.transport = transport


class ResponseTransportHeaders(object):
    """Response-specific Transport Headers"""

    # TODO implement __repr__

    __slots__ = (
        'failure_domain',
        'scheme',
    )

    def __init__(self,
                 failure_domain=None,
                 scheme=None,
                 **kwargs):

        if scheme is None:
            scheme = schemes.RAW

        self.failure_domain = failure_domain
        self.scheme = scheme


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
