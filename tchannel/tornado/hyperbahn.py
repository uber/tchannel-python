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
import json
import logging
import random

import tornado.gen
import tornado.ioloop

from .response import StatusCode

DELAY = 3 * 60 * 1000  # ms delay time for successful advertise
PER_ATTEMPT_TIMEOUT = 2.0  # seconds
FIRST_ADVERTISE_TIME = PER_ATTEMPT_TIMEOUT
DEFAULT_INTERVAL_MAX_JITTER_SECS = 5

log = logging.getLogger('tchannel')


class Advertiser(object):
    """Advertiser controls the advertise loop for Hyperbahn.

    :param service:
        Name to advertise as
    :param tchannel:
        ``tchannel.tornado.TChannel`` instance to use to advertise
    :param io_loop:
        IOLoop to schedule asynchronous operations. The current IOLoop will be
        used if one isn't specified.
    :param interval_secs:
        Interval (in milliseconds) at which new ``ad`` requests are broadcast.
        Defaults to 3 minutes.
    :param ttl_secs:
        Time (in seconds) to wait for a single ``ad`` request. Defaults to 2
        seconds.
    :param interval_max_jitter_secs:
        Variance allowed in the interval per request. Defaults to 5 seconds.
        The jitter applies to the initial advertise request as well.
    """

    def __init__(self, service, tchannel, interval_secs=None, ttl_secs=None,
                 interval_max_jitter_secs=None, io_loop=None):
        if interval_secs is None:
            interval_secs = DELAY / 1000.0
        if ttl_secs is None:
            ttl_secs = PER_ATTEMPT_TIMEOUT
        if interval_max_jitter_secs is None:
            interval_max_jitter_secs = DEFAULT_INTERVAL_MAX_JITTER_SECS

        self.service = service
        self.tchannel = tchannel

        self.interval_secs = interval_secs
        self.ttl_secs = ttl_secs
        self.interval_max_jitter_secs = interval_max_jitter_secs
        self.running = False
        self.io_loop = io_loop
        self._next_ad = None

    def start(self):
        """Starts the advertise loop.

        Returns the result of the first ad request.
        """
        if self.running:
            raise Exception('Advertiser is already running')
        if self.io_loop is None:
            self.io_loop = tornado.ioloop.IOLoop.current()

        self.running = True
        answer = tornado.gen.Future()
        self._schedule_ad(0, answer)
        return answer

    def stop(self):
        self.running = False
        if self._next_ad is not None:
            t, self._next_ad = self._next_ad, None
            self.io_loop.remove_timeout(t)

    def _schedule_ad(self, delay=None, response_future=None):
        """Schedules an ``ad`` request.

        :param delay:
            Time in seconds to wait before making the ``ad`` request. Defaults
            to self.interval_secs. Regardless of value, a jitter of
            self.interval_max_jitter_secs is applied to this.
        :param response_future:
            If non-None, the result of the advertise request is filled into
            this future.
        """
        if not self.running:
            return

        if delay is None:
            delay = self.interval_secs

        delay += random.uniform(0, self.interval_max_jitter_secs)
        self._next_ad = self.io_loop.call_later(delay, self._ad,
                                                response_future)

    @tornado.gen.coroutine
    def _ad(self, response_future=None):
        self._next_ad = None
        try:
            response = yield self.tchannel.request(service='hyperbahn').send(
                arg1='ad',  # advertise
                arg2='',
                arg3=json.dumps({
                    'services': [
                        {
                            'serviceName': self.service,
                            'cost': 0,
                        }
                    ]
                }),
                headers={'as': 'json'},
                retry_limit=0,
                ttl=self.ttl_secs,
            )
        except Exception as e:
            log.info('Failed to register with Hyperbahn: %s', e, exc_info=True)
            if response_future is not None:
                response_future.set_exc_info(sys.exc_info())
        else:
            if response.code != StatusCode.ok:
                log.info('Failed to register with Hyperbahn: %s', response)
            else:
                log.info('Successfully registered with Hyperbahn')
            if response_future is not None:
                response_future.set_result(response)
        finally:
            self.io_loop.spawn_callback(self._schedule_ad)


def advertise(tchannel, service, routers=None, timeout=None, router_file=None,
              jitter=None):
    """Advertise with Hyperbahn.

    See :py:class:`tchannel.TChannel.advertise`.
    """
    timeout = timeout or FIRST_ADVERTISE_TIME
    if routers is not None and router_file is not None:
        raise ValueError(
            'Only one of routers and router_file can be provided.')

    if routers is None and router_file is not None:
        # should just let the exceptions fly
        try:
            with open(router_file, 'r') as json_data:
                routers = json.load(json_data)
        except (IOError, OSError, ValueError):
            log.exception('Failed to read seed routers list.')
            raise

    for router in routers:
        # We use .get here instead of .add because we don't want to fail if a
        # TChannel already knows about some of the routers.
        tchannel.peers.get(router)

    adv = Advertiser(service, tchannel, ttl_secs=timeout,
                     interval_max_jitter_secs=jitter)
    return adv.start()


advertize = advertise  # just in case
