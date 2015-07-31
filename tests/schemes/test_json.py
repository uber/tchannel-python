from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
import tornado

from tchannel import TChannel, schemes
from tchannel import response
from tchannel.tornado import TChannel as DeprecatedTChannel


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register('endpoint', schemes.JSON)
    @tornado.gen.coroutine
    def endpoint(request, response, proxy):

        header = yield request.get_header()
        body = yield request.get_body()

        assert header == {'req': 'header'}
        assert body == {'req': 'body'}

        response.write_header({
            'resp': 'header'
        })
        response.write_body({
            'resp': 'body'
        })

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.json(
        service=server.hostport,
        endpoint='endpoint',
        header={'req': 'header'},
        body={'req': 'body'},
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.header == {'resp': 'header'}
    assert resp.body == {'resp': 'body'}

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.JSON
    assert resp.transport.failure_domain is None
