#!/usr/bin/env python
from __future__ import absolute_import

from tornado import ioloop
from tchannel import TChannel
from service import KeyValue


app = TChannel('thrift-benchmark', hostport='localhost:12345')


values = {'hello': 'world'}


@app.register(KeyValue)
def getValue(request, response, tchannel):
    key = request.args.key
    value = values.get(key)

    if value is None:
        raise KeyValue.NotFoundError(key)

    return value


@app.register(KeyValue)
def setValue(request, response, tchannel):
    key = request.args.key
    value = request.args.value
    values[key] = value


def run():
    app.listen()


if __name__ == '__main__':
    run()
    ioloop.IOLoop.current().start()
