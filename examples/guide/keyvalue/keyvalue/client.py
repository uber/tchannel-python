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
from tornado import gen
from tornado import ioloop
from tchannel import TChannel
from tchannel import thrift_request_builder

from service import KeyValue


# Note: When using Hyperbahn this `hostport` option is *NOT NEEDED*.
KeyValueClient = thrift_request_builder(
    service='keyvalue-server',
    thrift_module=KeyValue,
    hostport='localhost:8889',
)


@gen.coroutine
def run():
    app_name = 'keyvalue-client'

    tchannel = TChannel(app_name)

    KeyValueClient.setValue("foo", "Hello, world!"),

    yield tchannel.thrift(
        KeyValueClient.setValue("foo", "Hello, world!"),
    )

    response = yield tchannel.thrift(
        KeyValueClient.getValue("foo"),
    )

    print response.body


if __name__ == '__main__':
    ioloop.IOLoop.current().run_sync(run)
