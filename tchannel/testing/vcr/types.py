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

from collections import namedtuple


class Request(namedtuple('Request', 'service endpoint headers body')):
    """VCR's view of the request.

    This only includes information necessary to match requests.
    """

    def to_primitive(self):
        return {
            'service': self.service,
            'endpoint': self.endpoint,
            'headers': self.headers,
            'body': self.body,
        }

    @classmethod
    def to_native(cls, data):
        return cls(
            service=data['service'],
            endpoint=data['endpoint'],
            headers=data['headers'],
            body=data['body'],
        )


class Response(namedtuple('Response', 'status headers body')):
    """VCR's view of the response.

    This only includes information necessary to reproduce responses.
    """

    def to_primitive(self):
        return {
            'status': self.status,
            'headers': self.headers,
            'body': self.body,
        }

    @classmethod
    def to_native(cls, data):
        return cls(
            status=data['status'],
            headers=data['headers'],
            body=data['body'],
        )


class Interaction(namedtuple('Interaction', 'request response')):
    """An interaction is a request-response pair."""

    def to_primitive(self):
        return {
            'request': self.request.to_primitive(),
            'response': self.response.to_primitive(),
        }

    @classmethod
    def to_native(cls, data):
        return cls(
            request=Request.to_native(data['request']),
            response=Response.to_native(data['response']),
        )
