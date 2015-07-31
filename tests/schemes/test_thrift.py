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
    def testStruct(request, response, proxy):

        # assert request.header == {'req': 'header'}
        assert request.args.thing.string_thing == 'req string'

        # response.write_header({
        #    'resp': 'header'
        # })

        return ThriftTest.Xtruct(
            string_thing="resp string"
        )

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='ThriftTest',  # TODO service name ThriftTest is so confusing
        thrift_module=ThriftTest
    )

    resp = yield tchannel.thrift(
        request=service.testStruct(ThriftTest.Xtruct("req string")),
        header={'req': 'header'},
        hostport=server.hostport,  # TODO this shouldn't be necessary?
    )

    # verify response
    assert isinstance(resp, response.Response)
    # assert resp.header == {'resp': 'header'}
    assert resp.body == ThriftTest.Xtruct("resp string")

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.THRIFT
    assert resp.transport.failure_domain is None
