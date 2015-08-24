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

import threading

import tornado.ioloop

from tchannel import TChannel
from tchannel import Response


class UnexpectedCallException(Exception):
    pass


class _LimitCount(object):

    def __init__(self, function, count):
        self.remaining = count
        self.function = function

    def __call__(self, request, response):
        if self.remaining <= 0:
            raise UnexpectedCallException(
                'Received unexpected call to %s' % request.endpoint
            )

        self.remaining -= 1
        return self.function(request, response)


class Expectation(object):
    """Represents an expectation for the MockServer."""

    def __init__(self):
        self.execute = None

    def and_write(self, body, headers=None):

        def execute(request, response):
            if headers:
                response.headers = headers
            response.body = body
            return response

        self.execute = execute
        return self

    def and_result(self, result):

        def execute(request, response):
            return result

        self.execute = execute
        return self

    def and_raise(self, exc):

        def execute(request, response):
            raise exc

        self.execute = execute
        return self

    def times(self, count):
        self.execute = _LimitCount(self.execute, count)
        return self

    def once(self):
        return self.times(1)


class MockServer(object):
    TIMEOUT = 0.15

    def __init__(self, port=None, timeout=None):
        port = port or 0

        self.tchannel = TChannel(
            name='test',
            hostport="localhost:%s" % str(port),
        )

        self.timeout = timeout or self.TIMEOUT
        self.thread = None
        self.ready = False
        self.io_loop = None

    @property
    def port(self):
        return int(self.hostport.rsplit(':', 1)[1])

    @property
    def hostport(self):
        return self.tchannel.hostport

    def expect_call(self, endpoint, scheme='raw', **kwargs):
        assert isinstance(scheme, basestring)

        if not isinstance(endpoint, basestring):
            scheme = 'thrift'

        expectation = Expectation()

        def handle_expected_endpoint(request):
            response = Response()
            return expectation.execute(request, response)

        self.tchannel.register(
            scheme=scheme,
            endpoint=endpoint,
            handler=handle_expected_endpoint,
            **kwargs
        )

        return expectation

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self):
        assert self.thread is None, 'server already started'
        self.thread = threading.Thread(target=self.serve)
        self.thread.start()
        while not self.ready:
            pass

    def serve(self):
        self.io_loop = tornado.ioloop.IOLoop()
        self.io_loop.make_current()

        self.tchannel.listen()

        def callback():
            self.ready = True

        self.io_loop.add_callback(callback)
        self.io_loop.start()

    def stop(self):
        self.shutdown()
        self.thread.join()

    def shutdown(self):
        self.io_loop.stop()
