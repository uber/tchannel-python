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
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from tchannel.schemes import THRIFT

from .. import io
from .. import rw


class ThriftSerializer(object):

    name = THRIFT

    _headers_rw = rw.headers(
        rw.number(2),
        rw.len_prefixed_string(rw.number(2)),
        rw.len_prefixed_string(rw.number(2)),
    )

    __slots__ = ('module', 'deserialize_type')

    def __init__(self, module, deserialize_type):
        self.module = module
        self.deserialize_type = deserialize_type

    def serialize_header(self, headers):
        headers = headers or {}
        result = self._headers_rw.write(headers, io.BytesIO()).getvalue()
        return result

    def deserialize_header(self, headers):
        headers = headers or {}
        if headers:
            headers = io.BytesIO(headers)
            headers = self._headers_rw.read(headers)
        result = dict(headers)

        return result

    def serialize_body(self, obj):
        return self.module.dumps(obj)

    def deserialize_body(self, body):
        return self.module.loads(self.deserialize_type, body)
