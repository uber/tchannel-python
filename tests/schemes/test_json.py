from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest

from tchannel import TChannel, Response, schemes
from tchannel.response import ResponseTransportHeaders


@pytest.mark.gen_test
@pytest.mark.callz
def test_call_should_get_response():

    # Given this test server:

    server = TChannel(name='server')

    @server.json.register
    def endpoint(request):

        assert request.headers == {'req': 'headers'}
        assert request.body == {'req': 'body'}

        return Response({'resp': 'body'}, headers={'resp': 'headers'})

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.json(
        service='server',
        endpoint='endpoint',
        headers={'req': 'headers'},
        body={'req': 'body'},
        hostport=server.hostport,
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == {'resp': 'headers'}
    assert resp.body == {'resp': 'body'}

    # verify response transport headers
    assert isinstance(resp.transport, ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.JSON
    assert resp.transport.failure_domain is None


@pytest.mark.gen_test
@pytest.mark.callz
def test_endpoint_can_return_just_body():

    # Given this test server:

    server = TChannel(name='server')

    @server.json.register
    def endpoint(request):
        return {'resp': 'body'}

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.json(
        service='server',
        endpoint='endpoint',
        hostport=server.hostport,
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.body == {'resp': 'body'}
