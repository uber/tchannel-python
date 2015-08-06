from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
import tornado

from tchannel import TChannel, schemes
from tchannel import response


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    # Given this test server:

    server = TChannel(name='server')

    @server.register('endpoint', schemes.JSON)
    @tornado.gen.coroutine
    def endpoint(request, response, proxy):

        headers = yield request.get_header()
        body = yield request.get_body()

        assert headers == {'req': 'headers'}
        assert body == {'req': 'body'}

        response.write_header({
            'resp': 'headers'
        })
        response.write_body({
            'resp': 'body'
        })

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
    assert isinstance(resp, response.Response)
    assert resp.headers == {'resp': 'headers'}
    assert resp.body == {'resp': 'body'}

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.JSON
    assert resp.transport.failure_domain is None
