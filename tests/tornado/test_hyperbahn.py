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

import os
import json
import pytest
import tornado

from tchannel.errors import NetworkError
from tchannel.tornado import TChannel
from tchannel.tornado import hyperbahn


def test_new_client_establishes_peers():
    routers = ['127.0.0.1:2300' + str(i) for i in xrange(5)]

    # TChannel knows about one of the peers already.
    channel = TChannel('test', known_peers=['127.0.0.1:23002'])

    hyperbahn.advertise(
        channel,
        'baz',
        routers,
    )

    for router in routers:
        assert channel.peer_group.lookup(router)


def test_new_client_establishes_peers_from_file():

    host_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../data/hosts.json',
    )

    # TChannel knows about one of the peers already.
    channel = TChannel('test', known_peers=['127.0.0.1:23002'])

    hyperbahn.advertise(
        channel,
        'baz',
        None,
        None,
        host_path
    )

    with open(host_path, 'r') as json_data:
        routers = json.load(json_data)
    for router in routers:
        assert channel.peer_group.lookup(router)


@pytest.mark.gen_test
def test_advertise_should_raise_on_invalid_router_file():

    channel = TChannel(name='client')
    with pytest.raises(IOError):
        yield hyperbahn.advertise(
            channel,
            'baz',
            None,
            None,
            '?~~lala')

    with pytest.raises(ValueError):
        yield hyperbahn.advertise(
            channel,
            'baz',
            '?~~lala',
            None,
            '?~~lala')


@pytest.mark.gen_test
def test_request():
    channel = TChannel(name='test')
    hyperbahn.advertise(channel, 'foo', ['127.0.0.1:23000'])

    # Just want to make sure all the plumbing fits together.

    with pytest.raises(NetworkError):
        yield channel.request(service='bar').send(
            arg1='baz',
            arg2='bam',
            arg3='boo',
            headers={'as': 'qux'},
        )


@pytest.mark.gen_test
def test_advertise():
    server = TChannel(name="test_server")

    @server.register('ad', 'json')
    @tornado.gen.coroutine
    def ad(request, response):
        body = yield request.get_body()
        response.write_body(body)

    server.listen()
    channel = TChannel(name='test')

    response = yield hyperbahn.advertise(
        channel,
        'test', [server.hostport]
    )
    result = yield response.get_body()
    assert (
        result == '{"services": [{"serviceName": "test", "cost": 0}]}' or
        result == '{"services": [{"cost": 0, "serviceName": "test"}]}'
    )
