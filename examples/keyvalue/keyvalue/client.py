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
from tchannel.thrift import client_for
from tchannel.tornado import TChannel

from service import KeyValue


KeyValueClient = client_for('keyvalue-server', KeyValue)


@gen.coroutine
def run():
    app_name = 'keyvalue-client'

    app = TChannel(app_name)

    # Note: When using Hyperbahn this `hostport` option is *NOT NEEDED*.
    client = KeyValueClient(app, hostport='localhost:8889')

    yield client.setValue("foo", "bar")

    response = yield client.getValue("foo")

    print response


if __name__ == '__main__':
    ioloop.IOLoop.current().run_sync(run)
