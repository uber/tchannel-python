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

from functools import wraps

import mock
import contextlib2
from tornado import gen

from tchannel import schemes
from tchannel.errors import TChannelError
from tchannel.tornado import TChannel
from tchannel.tornado.response import Response
from tchannel.tornado.stream import maybe_stream
from tchannel.tornado.stream import read_full

from . import proxy


_TChannel_request = TChannel.request


@contextlib2.contextmanager
def force_reset():
    with contextlib2.ExitStack() as exit_stack:
        exit_stack.enter_context(
            mock.patch.object(TChannel, 'request', _TChannel_request)
        )
        yield


class PatchedClientOperation(object):

    def __init__(
        self,
        vcr_hostport,
        original_tchannel,
        hostport=None,
        service=None,
        arg_scheme=None,
        **kwargs
    ):
        self.vcr_hostport = vcr_hostport
        self.hostport = hostport or ''
        self.service = service or ''
        self.arg_scheme = arg_scheme or schemes.DEFAULT
        self.original_tchannel = original_tchannel

    @gen.coroutine
    def send(self, arg1, arg2, arg3,
             headers=None,
             ttl=None,
             **kwargs):
        arg1, arg2, arg3 = map(maybe_stream, [arg1, arg2, arg3])

        endpoint = yield read_full(arg1)

        headers = headers or {}
        headers.setdefault('as', self.arg_scheme)

        vcr_request = proxy.Request(
            serviceName=self.service.encode('utf-8'),
            hostPort=self.hostport,
            knownPeers=self.original_tchannel.peers.hosts,
            endpoint=endpoint,
            headers=(yield read_full(arg2)),
            body=(yield read_full(arg3)),
            argScheme=getattr(proxy.ArgScheme, self.arg_scheme.upper()),
            transportHeaders=[
                proxy.TransportHeader(bytes(k), bytes(v))
                for k, v in headers.items()
            ],
        )

        # TODO what to do with traceflag, attempt-times, ttl
        # TODO catch protocol errors

        from tchannel import TChannel
        tchannel = TChannel('proxy-client')

        with force_reset():
            vcr_response_future = tchannel.thrift(
                proxy.VCRProxy.send(vcr_request),
                hostport=self.vcr_hostport,
                timeout=float(ttl) * 1.1 if ttl else ttl,
                # If a timeout was specified, use that plus 10% to give some
                # leeway to the VCR proxy request itself.
            )

        try:
            vcr_response = yield vcr_response_future
        except proxy.RemoteServiceError as e:
            raise TChannelError.from_code(
                e.code,
                description=(
                    "The remote service threw a protocol error: %s" % (e,)
                )
            )

        response = Response(
            code=vcr_response.body.code,
            argstreams=[
                maybe_stream(endpoint),
                maybe_stream(vcr_response.body.headers),
                maybe_stream(vcr_response.body.body),
            ],
            # TODO headers=vcr_response.transportHeaders,
        )

        raise gen.Return(response)


class Patcher(object):
    """Monkey patches classes to use a VCRProxyClient to send requests."""

    def __init__(self, vcr_hostport):
        """
        :param vcr_hostport:
            Hostport at which VCRProxyService is running.
        """
        self.vcr_hostport = vcr_hostport
        self._exit_stack = contextlib2.ExitStack()

    def _patch_request(self):

        @wraps(_TChannel_request)
        def request(channel, *args, **kwargs):
            return PatchedClientOperation(
                self.vcr_hostport, channel, *args, **kwargs
            )

        return mock.patch.object(TChannel, 'request', request)

    def __enter__(self):
        self._exit_stack.enter_context(self._patch_request())

    def __exit__(self, *args):
        self._exit_stack.close()

    def __call__(self, function):
        # being used as a decorator

        @wraps(function)
        def new_function(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        return new_function
