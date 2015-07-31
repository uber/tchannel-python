from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import (
    TChannel, from_thrift_module,
    schemes, response
)
from tchannel.tornado import TChannel as DeprecatedTChannel
from tests.data.generated.ThriftTest import ThriftTest


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testString(request, response, proxy):

        assert request.header == {'req': 'header'}
        assert request.args.thing == "req string"

        response.write_header({
            'resp': 'header'
        })
        response.write_result("resp string")

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service=server.hostport,
        thrift_class=ThriftTest
    )

    resp = yield tchannel.thrift(
        tchannel=service.testString("req string"),
        header={'req': 'header'},
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.header == {'resp': 'header'}
    assert resp.body == "resp string"

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.THRIFT
    assert resp.transport.failure_domain is None
