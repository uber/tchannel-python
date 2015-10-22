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

from __future__ import absolute_import, print_function, unicode_literals

from tchannel.serializer.thrift import ThriftSerializer


class ThriftRequest(object):

    __slots__ = (
        'service', 'endpoint', 'result_type', 'call_args', 'hostport',
        '_serializer',
    )

    # TODO - implement __repr__

    # TODO we don't use a specialized ThriftResponse anywhere. Maybe we can
    # get rid of this too and just use plain Request objects.

    def __init__(self, module, service, endpoint, result_type, call_args,
                 hostport=None, serializer=None):
        self.service = service
        self.endpoint = endpoint
        self.result_type = result_type
        self.call_args = call_args
        self.hostport = hostport

        self._serializer = ThriftSerializer(module, result_type)

    def get_serializer(self):
        return self._serializer

    def read_body(self, body):
        response_spec = self.result_type.type_spec

        for exc_spec in response_spec.exception_specs:
            exc = getattr(body, exc_spec.name)
            if exc is not None:
                raise exc

        # success - non-void
        if response_spec.return_spec is not None:
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
