# Copyright (c) 2018 Uber Technologies, Inc.
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

import pytest
from tornado import gen

from tchannel import TChannel


@pytest.yield_fixture
def server(io_loop):
    server = TChannel('server')

    @server.json.register('hello')
    def hello(request):
        return 'world'

    server.listen()
    try:
        yield server
    finally:
        server.close()


@pytest.yield_fixture
def client(io_loop):
    client = TChannel('client')
    # The client listens for incoming connections so that the server doesn't
    # treat is as an ephemeral client. This is needed to exercise the p2p use
    # case.
    client.listen()
    try:
        yield client
    finally:
        client.close()


@pytest.yield_fixture
def routers(server, io_loop):
    routers = [TChannel('hyperbahn') for i in range(5)]

    # Generates an ad function for routers[i].
    def ad_for(me):
        # Sends a request to the server from all routers except this one.
        # This establishes an incoming connection from each router to the
        # server on advertise.
        @gen.coroutine
        def ad(request):

            futures = []
            for i, router in enumerate(routers):
                if i == me:
                    continue
                future = router.json(
                    'server', 'hello', 'world', hostport=server.hostport,
                )
                futures.append(future)
            yield futures
            raise gen.Return({})

        return ad

    for i, router in enumerate(routers):
        router.json.register('ad')(ad_for(i))
        router.listen()
    try:
        yield routers
    finally:
        for router in routers:
            router.close()


@pytest.mark.gen_test
def test_advertise_with_p2p(server, client, routers):
    # This test verifies that a server using a series of routers to send and
    # receive requests does not treat a directly-connected peer as a router as
    # well.

    yield server.advertise(routers=[r.hostport for r in routers])

    # Verify that all routers can receive requests.
    blacklist = set()
    remaining = {p.hostport for p in routers}
    while len(remaining):
        peer = server._dep_tchannel.peers.choose(blacklist=blacklist)
        assert peer, ("expected to find one of %s" % str(remaining))
        blacklist.add(peer.hostport)
        remaining.remove(peer.hostport)

    # Establish a p2p connection.
    yield client.json('server', 'hello', 'world', hostport=server.hostport)

    # Verify that all routers can still receive requests.
    blacklist = set()
    remaining = {p.hostport for p in routers}
    while len(remaining):
        peer = server._dep_tchannel.peers.choose(blacklist=blacklist)
        assert peer, ("expected to find one of %s" % str(remaining))
        blacklist.add(peer.hostport)
        remaining.remove(peer.hostport)

    # The p2p client should never be chosen to send requests.
    peer = server._dep_tchannel.peers.choose(blacklist=blacklist)
    assert not peer, "did not expect a peer"
