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

import sys
import random
import threading
from functools import wraps
from concurrent.futures import Future as ConcFuture

from tornado import gen
from tornado.ioloop import IOLoop

from tchannel.errors import TChannelError
from tchannel import TChannel

from . import proxy


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
                raise proxy.VCRServiceError(str(e))
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

        self.io_loop = None
        self.thread = None
        self.tchannel = None

        self._running = ConcFuture()

    @wrap_uncaught(reraise=(
        proxy.CannotRecordInteractionsError,
        proxy.NoPeersAvailableError,
        proxy.RemoteServiceError,
        proxy.VCRServiceError,
    ))
    @gen.coroutine
    def send(self, request):
        cassette = self.cassette
        request = request.body.request

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
            raise proxy.CannotRecordInteractionsError(
                'Could not find a matching response for request %s and the '
                'record mode %s prevents new interactions from being '
                'recorded. Your test may be performing an unexpected '
                'request.' % (str(request), cassette.record_mode)
            )

        peers = []
        if request.hostPort:
            peers = [request.hostPort]
        else:
            peers = request.knownPeers

        if not peers:
            raise proxy.NoPeersAvailableError(
                'Could not find a recorded response for request %s and was '
                'unable to make a new request because both, hostPort and '
                'knownPeers were unspecified. One of them must be specified '
                'for me to make new requests. Make sure you specified a '
                'hostport in the original request or are advertising '
                'on Hyperbahn.' % (str(request),)
            )

        arg_scheme = proxy.ArgScheme.name_of(request.argScheme).lower()

        with self.unpatch():
            # TODO propagate other request and response parameters
            # TODO might make sense to tag all VCR requests with a protocol
            # header of some kind
            response_future = self.tchannel._dep_tchannel.request(
                service=request.serviceName,
                arg_scheme=arg_scheme,
                hostport=random.choice(peers),
            ).send(
                request.endpoint,
                request.headers,
                request.body,
                headers={h.key: h.value for h in request.transportHeaders},
            )

        # Don't actually yield while everything is unpatched.
        try:
            response = yield response_future
        except TChannelError as e:
            raise proxy.RemoteServiceError(
                code=e.code,
                message=str(e),
            )
        response_headers = yield response.get_header()
        response_body = yield response.get_body()

        vcr_response = proxy.Response(
            code=response.status_code,
            headers=response_headers,
            body=response_body,
        )
        cassette.record(request, vcr_response)
        raise gen.Return(vcr_response)

    @property
    def hostport(self):
        return self.tchannel.hostport

    def _run(self):
        self.io_loop = IOLoop()
        self.io_loop.make_current()

        self.tchannel = TChannel('proxy-server')

        # Hack around legacy TChannel
        from tchannel.thrift import rw as thriftrw
        thriftrw.register(
            self.tchannel._dep_tchannel._handler,
            proxy.VCRProxy,
            handler=self.send,
        )

        try:
            self.tchannel.listen()
            self._running.set_result(None)
        except Exception:
            self._running.set_exception_info(*sys.exc_info()[1:])
        else:
            self.io_loop.start()

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

        self._running.result(1)  # seconds

    def stop(self):
        self.tchannel._dep_tchannel.close()
        self.tchannel = None

        self.io_loop.stop()
        self.io_loop = None

        self.thread.join(1)  # seconds
        self.thread = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
