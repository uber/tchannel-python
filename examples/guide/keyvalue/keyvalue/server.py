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

from tornado import ioloop
from tchannel import TChannel, thrift

tchannel = TChannel('keyvalue-service', hostport='localhost:8889')
service = thrift.load('examples/guide/keyvalue/service.thrift')

values = {'hello': 'world'}


@tchannel.thrift.register(service.KeyValue)
def getValue(request):
    key = request.body.key
    value = values.get(key)

    if value is None:
        raise service.NotFoundError(key)

    return value


@tchannel.thrift.register(service.KeyValue)
def setValue(request):
    key = request.body.key
    value = request.body.value
    values[key] = value


def run():
    tchannel.listen()


if __name__ == '__main__':
    run()
    ioloop.IOLoop.current().start()
