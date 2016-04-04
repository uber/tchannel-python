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

import json

from tchannel.schemes import JSON


class JsonSerializer(object):
    name = JSON

    def serialize_header(self, headers):
        headers = headers or {}

        for k, v in headers.iteritems():
            if not (isinstance(k, basestring) and isinstance(v, basestring)):
                raise ValueError(
                    'headers must be a map[string]string (a shallow dict '
                    'where keys and values are strings)'
                )

        return json.dumps(headers)

    def deserialize_header(self, headers):
        if not headers:
            return {}
        return json.loads(headers)

    def deserialize_body(self, obj):
        return json.loads(obj)

    def serialize_body(self, obj):
        return json.dumps(obj)
