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

from __future__ import (
    absolute_import, print_function, unicode_literals, division
)

from tchannel import TChannel
from tchannel.tornado import hyperbahn

import pytest
from tornado import gen


class HyperbahnBlackhole(object):

    def __init__(self, count=None):
        if count is None:
            count = 10

        self.tchannels = [TChannel('hyperbahn') for x in range(count)]
        self.ad_count = 0

        for tch in self.tchannels:
            tch.json.register('ad')(self._advertise_blackhole)

    @gen.coroutine
    def _advertise_blackhole(self, request):
        self.ad_count += 1

        # succeed the first ad attempt so that we start the loop
        if self.ad_count == 1:
            raise gen.Return({})

        # don't respond to any other ads
        yield gen.sleep(10000)

    @property
    def peers(self):
        return [tch.hostport for tch in self.tchannels]

    def start(self):
        for tch in self.tchannels:
            tch.listen()

    def stop(self):
        for tch in self.tchannels:
            tch.close()


@pytest.yield_fixture
def blackhole(io_loop):
    hb = HyperbahnBlackhole()
    try:
        hb.start()
        yield hb
    finally:
        hb.stop()


@pytest.mark.gen_test
def test_ad_blackhole(blackhole, monkeypatch):
    # start new ad requests more frequently
    monkeypatch.setattr(hyperbahn, 'DELAY', 100)  # milliseconds
    monkeypatch.setattr(hyperbahn, 'PER_ATTEMPT_TIMEOUT', 5)  # seconds

    # No jitter
    monkeypatch.setattr(hyperbahn, 'DEFAULT_INTERVAL_MAX_JITTER_SECS', 0.0)

    # verify that we don't go crazy if Hyperbahn starts blackholing requests.
    client = TChannel('client')
    client.advertise(routers=blackhole.peers)
    yield gen.sleep(0.5)

    # The second ad request is still ongoing so no other ads should have been
    # made.
    assert 2 == blackhole.ad_count
