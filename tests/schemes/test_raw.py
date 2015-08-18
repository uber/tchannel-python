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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel, Request, Response, schemes
from tchannel.response import TransportHeaders


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    # Given this test server:

    server = TChannel(name='server')

    @server.raw.register
    def endpoint(request):

        assert isinstance(request, Request)
        assert request.headers == 'req headers'
        assert request.body == 'req body'

        return Response('resp body', headers='resp headers')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.raw(
        service='server',
        endpoint='endpoint',
        headers='req headers',
        body='req body',
        hostport=server.hostport,
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == 'resp headers'
    assert resp.body == 'resp body'

    # verify response transport headers
    assert isinstance(resp.transport, TransportHeaders)
    assert resp.transport.scheme == schemes.RAW
    assert resp.transport.failure_domain is None


@pytest.mark.gen_test
@pytest.mark.call
def test_register_should_work_with_different_endpoint():

    # Given this test server:

    server = TChannel(name='server')

    @server.raw.register('foo')
    def endpoint(request):
        return 'resp body'

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.raw(
        service='server',
        endpoint='foo',
        hostport=server.hostport,
    )

    assert resp.body == 'resp body'
