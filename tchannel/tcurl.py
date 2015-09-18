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

# Here's a good reference if you're touching this file and
# unfamiliar with argparse:
#
#   https://mkaz.github.io/2014/07/26/python-argparse-cookbook/
#

"""
tcurl: curl for tchannel applications

examples:

    Health check the "larry" service:

      tcurl.py --health --service larry


    Send a Thrift request to "larry":

      tcurl.py --thrift larry.thrift --service larry --endpoint Larry::nyuck \\
      --body '{"nyuck": "nyuck"}'
"""

from __future__ import absolute_import

import argparse
import logging
import json
import sys

import tornado.ioloop
import tornado.gen

from . import TChannel
from . import thrift
from .health import Meta

log = logging.getLogger('tchannel')


class Formatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    pass


def parse_args(args=None):

    args = args or sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=Formatter,
    )

    parser.add_argument(
        "--service", "-s",
        dest="service",
        default=None,
        required=True,
        help=(
            "Name of destination service for Hyperbahn routing."
        ),
    )

    parser.add_argument(
        "--host", "-p",
        dest="host",
        default="localhost:21300",
        help="Hostname and port to contact.",
    )

    parser.add_argument(
        "--endpoint", "-1",
        dest="endpoint",
        default="",
        help=(
            "Name of destination service for Hyperbahn routing."
        ),
    )

    parser.add_argument(
        "--headers", "-2",
        dest="headers",
        default=None,
        type=json.loads,
        help=(
            ", e.g., --headers foo=bar zip=zap."
        ),
    )

    parser.add_argument(
        "--body", "-3",
        dest="body",
        default=None,
        help=(
            "For Thrift requests this will be a JSON structure that maps "
            "cleanly onto the provided Thrift interface."
        ),
    )

    parser.add_argument(
        "--timeout",
        dest="timeout",
        default=1.0,
        type=float,
        help=(
            "Timeout, in seconds, for the request."
        ),
    )

    parser.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        help="Say more.",
    )

    thrift_group = parser.add_argument_group('thrift')

    thrift_group.add_argument(
        "--thrift", "-t",
        dest="thrift",
        type=argparse.FileType('r'),
        help=(
            "Path to a Thrift IDL file. Incompatible with --json."
        ),
    )
    thrift_group.add_argument(
        "--health",
        action="store_true",
        help=(
            "Perform a health check against the given service. This is "
            "overridden if --endpoint is provided."
        ),
    )

    json_group = parser.add_argument_group('json')

    json_group.add_argument(
        "--json", "-j", "-J",
        dest="json",
        action="store_true",
        help=(
            "Path to a Thrift IDL file. Incompatible with --thrfit."
        ),
    )

    args = parser.parse_args(args)

    if args.thrift or args.json:
        try:
            args.body = json.loads(args.body) if args.body else {}
        except ValueError:
            return parser.error("--body isn't valid JSON")

    if args.thrift and not args.endpoint:
        return parser.error("--thrift must be used with --endpoint")

    if args.json and not args.endpoint:
        return parser.error("--json must be used with --endpoint")

    if args.thrift and '::' not in args.endpoint:
        return parser.error(
            "--endpoint should be of the form ThriftService::methodName"
        )

    return args


def tcurl(tchannel, host, endpoint, headers, body, service):

    request = tchannel.request(host, service)

    return request.send(
        endpoint,
        headers,
        body,
    )


@tornado.gen.coroutine
def main(argv=None):
    args = parse_args(argv)

    tchannel = TChannel(name='tcurl.py')

    if args.health:
        args.endpoint = 'Meta::health'

        # HACK
        Meta._module.service = args.service
        Meta._module.hostport = args.host

        result = yield tchannel.thrift(
            Meta.health(),
            headers=args.headers,
            timeout=args.timeout,
        )

        print 'ok' if result.body.ok else 'notOk'
        raise tornado.gen.Return(result)

    if args.thrift:
        thrift_module = thrift.load(
            path=args.thrift.name,
            service=args.service,
            hostport=args.host,
        )

        thrift_service_name, thrift_method_name = args.endpoint.split('::')

        thrift_service = getattr(thrift_module, thrift_service_name)
        thrift_method = getattr(thrift_service, thrift_method_name)

        result = yield tchannel.thrift(
            thrift_method(**args.body),
            timeout=args.timeout,
            headers=args.headers,
        )

        print result.body
        raise tornado.gen.Return(result)

    if args.json:

        result = yield tchannel.json(
            service=args.service,
            endpoint=args.endpoint,
            body=args.body,
            headers=args.headers,
            timeout=args.timeout,
            hostport=args.host,
        )

        print result.body
        raise tornado.gen.Return(result)

    result = yield tchannel.raw(
        service=args.service,
        endpoint=args.endpoint,
        body=args.body,
        headers=args.headers,
        timeout=args.timeout,
        hostport=args.host,
    )

    print result.body
    raise tornado.gen.Return(result)


def start_ioloop():  # pragma: no cover
    ioloop = tornado.ioloop.IOLoop.current()
    ioloop.run_sync(main)


if __name__ == '__main__':  # pragma: no cover
    start_ioloop()
