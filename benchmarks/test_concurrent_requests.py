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
    absolute_import, unicode_literals, print_function, division
)

from tornado import gen, ioloop
from tchannel import TChannel


servers = None
client = None


def setup_server(num):
    servers = []
    for i in xrange(num):
        server = TChannel('server' + str(i))

        @server.raw.register
        def hello(request):
            return 'hello'
        server.listen()
        servers.append(server)
    return servers


@gen.coroutine
def setup_client(servers):
    router = []
    for i in xrange(1000):
        router.append('1.1.1.1:'+str(i))
    client = TChannel('client', known_peers=router)

    @client.raw.register
    def hello(request):
        return 'hello'
    client.listen()

    for i in xrange(100):
        server = servers[i]
        yield server.raw(
            service='server',
            endpoint='hello',
            body='hi',
            hostport=client.hostport,
        )

    raise gen.Return(client)


@gen.coroutine
def peer_test():
    global client
    fs = []
    for _ in xrange(100):
        fs.append(client.raw(
            service='server',
            endpoint='hello',
            body='hi',
            timeout=1000
        ))
    yield fs


def stress_test():
    ioloop.IOLoop.current().run_sync(peer_test)


@gen.coroutine
def setup():
    global servers, client
    servers = setup_server(100)
    client = yield setup_client(servers)


def test_peer_heap(benchmark):
    ioloop.IOLoop.current().run_sync(setup)
    benchmark(stress_test)
