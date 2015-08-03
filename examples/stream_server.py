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

from __future__ import absolute_import

import tornado.ioloop

from handlers import register_example_endpoints
from options import get_args
from tchannel.tornado import TChannel
from tchannel.tornado.stream import InMemStream


def main():
    args = get_args()

    app = TChannel(
        name='stream-server',
        hostport='%s:%d' % (args.host, args.port),
    )

    register_example_endpoints(app)

    @tornado.gen.coroutine
    def say_hi_stream(request, response, proxy):
        out_stream = InMemStream()
        response.set_body_s(out_stream)

        # TODO: Need to be able to flush without closing the stream.
        for character in 'Hello, world!':
            yield out_stream.write(character)

    app.register(endpoint="hi-stream", handler=say_hi_stream)

    app.listen()

    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':  # pragma: no cover
    main()
