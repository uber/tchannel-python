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

import json

from tchannel import thrift
from tchannel.sync import TChannel

tchannel = TChannel('thrift-client')
service = thrift.load(
    path='tests/data/idls/ThriftTest.thrift',
    service='thrift-server',
    hostport='localhost:54498',
)


def make_requests():

    # Fan-out
    futures = [tchannel.thrift(
        request=service.ThriftTest.testString(thing="req"),
        headers={
            'req': 'header',
        },
    ) for _ in xrange(20)]

    # Fan-in
    for future in futures:
        response = future.result()

    return response


resp = make_requests()

assert resp.headers == {
    'resp': 'header',
}
assert resp.body == 'resp' * 100000

print resp.body[:4]
print json.dumps(resp.headers)
