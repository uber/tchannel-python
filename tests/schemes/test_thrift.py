from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
import tornado

from tchannel import (
    TChannel, from_thrift_class,
    schemes, response
)
from tchannel.tornado import TChannel as DeprecatedTChannel
from tests.data.generated.ThriftTest import ThriftTest


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():
    return

    assert ThriftTest

    return

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register('endpoint', schemes.THRIFT)
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
    service = from_thrift_class(ThriftTest)

    resp = yield tchannel.thrift(
        rpc=service.getItem("key"),
        header={'req': 'header'},
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.header == {'resp': 'header'}
    assert resp.body == {'resp': 'body'}

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.JSON
    assert resp.transport.failure_domain is None
