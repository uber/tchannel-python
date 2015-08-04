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

        assert request.args.thing.string_thing == 'req string'

        return ThriftTest.Xtruct(
            string_thing="resp string"
        )

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='service',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    resp = yield tchannel.thrift(
        service.testStruct(ThriftTest.Xtruct("req string"))
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body == ThriftTest.Xtruct("resp string")

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.THRIFT
    assert resp.transport.failure_domain is None


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response_with_application_headers():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testStruct(request, response, proxy):

        # TODO server getting headers in non-friendly format,
        # create a top-level request that has friendly headers :)
        # assert request.headers == {'req': 'headers'}
        assert request.headers == [['req', 'header']]
        assert request.args.thing.string_thing == 'req string'

        # TODO should this response object be shared w client case?
        # TODO are we ok with the approach here? it's diff than client...
        # response.write_header({
        #    'resp': 'header'
        # })
        response.write_header('resp', 'header')

        return ThriftTest.Xtruct(
            string_thing="resp string"
        )

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='service',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    resp = yield tchannel.thrift(
        service.testStruct(ThriftTest.Xtruct("req string")),
        headers={'req': 'header'},
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.headers == {'resp': 'header'}
    assert resp.body == ThriftTest.Xtruct("resp string")

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.THRIFT
    assert resp.transport.failure_domain is None


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_application_exception():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testMultiException(request, response, proxy):

        if request.args.arg0 == 'Xception':
            raise ThriftTest.Xception(
                errorCode=1001,
                message='This is an Xception',
            )
        elif request.args.arg0 == 'Xception2':
            raise ThriftTest.Xception2(
                errorCode=2002
            )

        return ThriftTest.Xtruct(string_thing=request.args.arg1)

    server.listen()

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='service',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    with pytest.raises(ThriftTest.Xception):
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception', arg1='thingy')
        )

    with pytest.raises(ThriftTest.Xception2):
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception2', arg1='thingy')
        )
