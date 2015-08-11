#!/usr/bin/env python
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
