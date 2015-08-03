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
import sys

import tornado
import tornado.ioloop

from options import get_parser
from tchannel.tornado import TChannel
from tchannel.tornado.stream import PipeStream


@tornado.gen.coroutine
def send_stream(arg1, arg2, arg3, host):
    tchannel = TChannel(
        name='stream-client',
    )

    response = yield tchannel.request(host).send(
        arg1,
        arg2,
        arg3,
    )

    # Call get_body() to wait for the call to conclude; use
    # get_body_s to read the stream as it comes.
    body = yield response.get_body()
    print body


def main():
    parser = get_parser()
    parser.add_argument(
        "--file",
        dest="filename"
    )
    args = parser.parse_args()

    hostport = "%s:%s" % (args.host, args.port)

    arg1 = 'hi-stream'
    arg2 = None
    arg3 = None

    ioloop = tornado.ioloop.IOLoop.current()

    if args.filename == "stdin":
        arg3 = PipeStream(sys.stdin.fileno())
        send_stream(arg1, arg2, arg3, hostport)
        return ioloop.start()
    elif args.filename:
        f = os.open(args.filename, os.O_RDONLY)
        arg3 = PipeStream(f)
    else:
        arg3 = 'foo'

    ioloop.run_sync(lambda: send_stream(arg1, arg2, arg3, hostport))


if __name__ == '__main__':  # pragma: no cover
    main()
