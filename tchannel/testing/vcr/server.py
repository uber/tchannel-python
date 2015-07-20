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

from functools import wraps

from tornado import gen

from tchannel.errors import ProtocolError
from tchannel.tornado import TChannel

from .proxy import VCRProxy


def wrap_uncaught(func=None, reraise=None):
    """Catches uncaught exceptions and raises VCRServiceErrors instead.

    :param reraise:
        Collection of exception clasess that should be re-raised as-is.
    """
    reraise = reraise or ()

    def decorator(f):

        @wraps(f)
        @gen.coroutine
        def new_f(*args, **kwargs):
            try:
                result = yield gen.maybe_future(f(*args, **kwargs))
            except Exception as e:
                if any(isinstance(e, cls) for cls in reraise):
                    # TODO maybe use traceback.format_exc to also send a
                    # traceback?
                    raise e
                raise VCRProxy.VCRServiceError(e.message)
            else:
                raise gen.Return(result)

        return new_f

    if func is not None:
        return decorator(func)
    else:
        return decorator


class VCRProxyService(object):

    def __init__(self, cassette, unpatch):
        """
        :param unpatch:
            A function returning a context manager which temporarily unpatches
            any monkey patched code so that a real request can be made.
        :param cassette:
            Cassette being played.
        """
        self.unpatch = unpatch
        self.cassette = cassette

        self.tchannel = TChannel('proxy-server')
        self.tchannel.register(VCRProxy, handler=self.send)

    @wrap_uncaught(reraise=(
        VCRProxy.CannotRecordInteractionsError,
        VCRProxy.RemoteServiceError,
        VCRProxy.VCRServiceError,
    ))
    @gen.coroutine
    def send(self, request, response, channel):
        cassette = self.cassette
        request = request.args.request

        # TODO decode requests and responses based on arg scheme into more
        # readable formats.

        # Because Thrift doesn't handle UTF-8 correctly right now
        request.serviceName = request.serviceName.decode('utf-8')
        request.endpoint = request.endpoint.decode('utf-8')

        # TODO do we care about hostport being the same?
        if cassette.can_replay(request):
            vcr_response = cassette.replay(request)
            raise gen.Return(vcr_response)

        if cassette.write_protected:
            raise VCRProxy.CannotRecordInteractionsError(
                'Could not find a matching response for request %s and the '
                'record mode %s prevents new interactions from being '
                'recorded. Your test may be performing an uenxpected '
                'request.' % (str(request), cassette.record_mode)
            )

        arg_scheme = VCRProxy.ArgScheme.to_name(request.argScheme).lower()

        with self.unpatch():
            # TODO propagate other request and response parameters
            # TODO might make sense to tag all VCR requests with a protocol
            # header of some kind
            response_future = channel.request(
                service=request.serviceName,
                arg_scheme=arg_scheme,
                hostport=request.hostPort,
            ).send(
                request.endpoint,
                request.headers,
                request.body,
                headers={h.key: h.value for h in request.transportHeaders},
            )

        # Don't actually yield while everything is unpatched.
        try:
            response = yield response_future
        except ProtocolError as e:
            raise VCRProxy.RemoteServiceError(
                code=e.code,
                message=e.message,
            )
        response_headers = yield response.get_header()
        response_body = yield response.get_body()

        vcr_response = VCRProxy.Response(
            response.status_code,
            response_headers,
            response_body,
        )
        cassette.record(request, vcr_response)
        raise gen.Return(vcr_response)

    @property
    def hostport(self):
        return self.tchannel.hostport

    def start(self):
        self.tchannel.listen()

    def stop(self):
        self.tchannel.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
