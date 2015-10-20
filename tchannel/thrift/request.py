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

from tchannel.errors import ValueExpectedError
from tchannel.serializer.thrift import ThriftSerializer


class ThriftRequest(object):

    __slots__ = (
        'service', 'endpoint', 'result_type', 'call_args', 'hostport',
        '_serializer',
    )

    # TODO - implement __repr__

    def __init__(self, service, endpoint, result_type,
                 call_args, hostport=None, serializer=None):

        self.service = service
        self.endpoint = endpoint
        self.result_type = result_type
        self.call_args = call_args
        self.hostport = hostport

        if not serializer:
            serializer = ThriftSerializer(self.result_type)
        self._serializer = serializer

    def get_serializer(self):
        return self._serializer

    def read_body(self, body):
        """Handles the response body for this request.

        If the response body includes a result, returns the result unwrapped
        from the response union. If the response contains an exception, raises
        that exception.
        """
        result_spec = self.result_type.thrift_spec

        # raise application exception, if present
        for exc_spec in result_spec[1:]:
            exc = getattr(body, exc_spec[2])
            if exc is not None:
                raise exc

        # success - non-void
        if len(result_spec) >= 1 and result_spec[0] is not None:

            # value expected, but got none
            # TODO - server side should use this same logic
            if body.success is None:
                raise ValueExpectedError(
                    'Expected a value to be returned for %s, '
                    'but recieved None - only void procedures can '
                    'return None.' % self.endpoint
                )

            return body.success

        # success - void
        else:
            return None
