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

import os
import json
import pytest
from tornado import gen

from tchannel.errors import NoAvailablePeerError, UnexpectedError
from tchannel.tornado import TChannel
from tchannel.tornado import hyperbahn
from six.moves import range


def test_new_client_establishes_peers():
    routers = ['127.0.0.1:2300' + str(i) for i in range(5)]

    # TChannel knows about one of the peers already.
    channel = TChannel('test', known_peers=['127.0.0.1:23002'])

    hyperbahn.advertise(
        channel,
        'baz',
        routers,
    )

    for router in routers:
        assert channel.peers.lookup(router)


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
        assert channel.peers.lookup(router)


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

    with pytest.raises(NoAvailablePeerError):
        yield channel.request(service='bar').send(
            arg1='baz',
            arg2='bam',
            arg3='boo',
            headers={'as': 'qux'},
        )


class Fakebahn(object):

    def __init__(self, handle):
        self.tchannel = TChannel(name='hyperbahn')
        self.count = 0  # number of ad requests received

        @self.tchannel.register('ad', 'json')
        @gen.coroutine
        def ad(request, response):
            self.count += 1
            yield handle(request, response)

    @property
    def hostport(self):
        return self.tchannel.hostport

    def start(self):
        self.tchannel.listen()

    def stop(self):
        self.tchannel.close()


@pytest.yield_fixture
def echobahn(io_loop):
    """A Hyperbahn that just echoes requests back."""

    @gen.coroutine
    def echo(request, response):
        body = yield request.get_body()
        response.write_body(body)

    server = Fakebahn(echo)
    try:
        server.start()
        yield server
    finally:
        server.stop()


@pytest.mark.gen_test
def test_advertise(echobahn):
    channel = TChannel(name='test')

    response = yield hyperbahn.advertise(channel, 'test', [echobahn.hostport])
    result = yield response.get_body()
    assert (
        result == b'{"services": [{"serviceName": "test", "cost": 0}]}' or
        result == b'{"services": [{"cost": 0, "serviceName": "test"}]}'
    )


@pytest.mark.gen_test
def test_advertiser_stop(echobahn):
    adv = hyperbahn.Advertiser(
        'foo', TChannel('foo', known_peers=[echobahn.hostport]),
        interval_secs=0.2,
        interval_max_jitter_secs=0.0,
    )
    yield adv.start()
    assert 1 == echobahn.count

    yield gen.sleep(0.25)
    assert 2 == echobahn.count

    adv.stop()

    yield gen.sleep(0.25)
    assert 2 == echobahn.count

    adv.stop()  # no-op
    assert 2 == echobahn.count


@pytest.mark.gen_test
def test_advertiser_fail_to_start():

    @gen.coroutine
    def fail(request, response):
        raise Exception('great sadness')

    hb = Fakebahn(fail)
    try:
        hb.start()
        adv = hyperbahn.Advertiser(
            'foo', TChannel('foo', known_peers=[hb.hostport]),
        )

        with pytest.raises(UnexpectedError) as exc_info:
            yield adv.start()

        assert 'great sadness' in str(exc_info)
        assert 1 == hb.count
    finally:
        hb.stop()


@pytest.mark.gen_test
def test_advertiser_fail():
    @gen.coroutine
    def fail(request, response):
        body = yield request.get_body()
        if hb.count == 1:
            # fail only the first request
            response.status_code = 1
        response.write_body(body)

    hb = Fakebahn(fail)
    try:
        hb.start()
        adv = hyperbahn.Advertiser(
            'foo', TChannel('foo', known_peers=[hb.hostport]),
            interval_secs=0.2,
            interval_max_jitter_secs=0.0,
        )

        yield adv.start()
        assert 1 == hb.count

        yield gen.sleep(0.25)
        assert 2 == hb.count
    finally:
        hb.stop()


@pytest.mark.gen_test
def test_advertiser_start_twice(echobahn):
    adv = hyperbahn.Advertiser(
        'foo', TChannel('foo', known_peers=[echobahn.hostport]),
    )
    yield adv.start()

    with pytest.raises(Exception) as exc_info:
        yield adv.start()

    assert 'already running' in str(exc_info)
    assert 1 == echobahn.count


@pytest.mark.gen_test
def test_advertiser_intermediate_failure():

    @gen.coroutine
    def handle(request, response):
        body = yield request.get_body()
        if hb.count == 2:
            # fail the second request only
            raise Exception('great sadness')
        response.write_body(body)

    hb = Fakebahn(handle)
    try:
        hb.start()
        adv = hyperbahn.Advertiser(
            'foo', TChannel('foo', known_peers=[hb.hostport]),
            interval_secs=0.2,
            interval_max_jitter_secs=0.0,
        )

        yield adv.start()
        assert 1 == hb.count

        yield gen.sleep(0.25)
        assert 2 == hb.count

        yield gen.sleep(0.25)
        assert 3 == hb.count
    finally:
        hb.stop()
