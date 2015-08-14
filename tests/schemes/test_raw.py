from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel, Request, Response, schemes
from tchannel.response import ResponseTransportHeaders


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
    assert isinstance(resp.transport, ResponseTransportHeaders)
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


@pytest.mark.gen_test
@pytest.mark.call
@pytest.mark.xfail  # TODO register programmatically is broke
def test_register_should_work_programatically():

    # Given this test server:

    server = TChannel(name='server')

    def endpoint(request):
        return 'resp body'

    server.raw.register('bar', handler=endpoint)
    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.raw(
        service='server',
        endpoint='bar',
        hostport=server.hostport,
    )

    assert resp.body == 'resp body'
