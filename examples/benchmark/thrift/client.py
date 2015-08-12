#!/usr/bin/env python

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

import os
import threading

from tornado import gen, ioloop
from tchannel import TChannel
from tchannel import thrift_request_builder
from service import KeyValue


tchannel = TChannel('thrift-benchmark-client')

kv = thrift_request_builder(
    service='thrift-benchmark',
    thrift_module=KeyValue,
    hostport='localhost:12345'
)

local = threading.local()
local.requests = 0


def report_work():
    print local.requests
    local.requests = 0


@gen.coroutine
def do_work():
    global requests

    # TODO: make this configurable
    data = os.urandom(4096)

    while True:
        yield tchannel.thrift(
            request=kv.setValue("key", data),
        )
        local.requests += 1

        # TODO: get/set ratio
        yield tchannel.thrift(
            request=kv.getValue("key"),
        )
        local.requests += 1


ioloop.PeriodicCallback(report_work, 1000).start()

resp = ioloop.IOLoop.current().run_sync(do_work)
