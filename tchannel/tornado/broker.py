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

import tornado

from ..errors import InvalidEndpointError
from ..errors import InvalidMessageError
from ..errors import TChannelError
from ..scheme import RawArgScheme
from .stream import Stream


class ArgSchemeBroker(object):
    """Use serializer to broker request/response."""

    def __init__(self, arg_scheme=None):
        self.endpoint = {}
        self.arg_scheme = arg_scheme or RawArgScheme()

    def register(self, rule, handler):
        """Register handler.

        :param rule: endpoint
        :param handler: endpoint handler
        """
        self.endpoint[rule] = handler

    def handle_call(self, req, resp, proxy):
        if not req.headers.get('as', None) == self.arg_scheme.type():
            raise InvalidMessageError(
                "Invalid arg scheme in request header"
            )

        req.scheme = self.arg_scheme
        resp.scheme = self.arg_scheme

        handler = self.endpoint.get(req.endpoint, None)
        if handler is None:
            raise InvalidEndpointError(
                "Endpoint '%s' for service '%s' is not defined" % (
                    req.endpoint, req.service
                )
            )

        return handler(req, resp, proxy)

    @tornado.gen.coroutine
    def send(self,
             client,  # operation?
             endpoint,
             header,
             body,  # NOTE body==call_args
             protocol_headers=None,
             traceflag=None,
             attempt_times=None,
             ttl=None,
             retry_delay=None):
        """Serialize and deserialize header and body into certain format
            based on arg scheme.
        See parameters definitions in
            :func:`tchannel.tornado.peer.PeerClientOperation.send`
        """
        try:
            if not isinstance(header, Stream):
                raw_header = self.arg_scheme.serialize_header(header)
            else:
                raw_header = header

            if not isinstance(body, Stream):
                raw_body = self.arg_scheme.serialize_body(body)
            else:
                raw_body = body

        except Exception as e:
            raise TChannelError(e.message)

        protocol_headers = protocol_headers or {}
        protocol_headers['as'] = self.arg_scheme.type()
        resp = yield client.send(
            endpoint,
            raw_header,
            raw_body,
            headers=protocol_headers,
            traceflag=traceflag,
            attempt_times=attempt_times,
            ttl=ttl,
            retry_delay=retry_delay,
        )

        resp.scheme = self.arg_scheme

        raise tornado.gen.Return(resp)
