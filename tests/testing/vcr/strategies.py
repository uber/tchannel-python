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

from hypothesis.strategies import (
    binary,
    builds,
    lists,
    sampled_from,
    text,
)

from tchannel.testing.vcr import proxy

arg_schemes = sampled_from(proxy.ArgScheme.values)

transport_headers = builds(
    proxy.TransportHeader,
    key=binary(),
    value=binary(),
)


requests = builds(
    proxy.Request,
    serviceName=text(),
    hostPort=sampled_from(('localhost', '')),
    endpoint=text(min_size=1),
    headers=binary(),
    body=binary(),
    argScheme=arg_schemes,
    transportHeaders=lists(transport_headers),
)


responses = builds(
    proxy.Response,
    code=sampled_from(proxy.StatusCode.values),
    headers=binary(),
    body=binary(),
)
