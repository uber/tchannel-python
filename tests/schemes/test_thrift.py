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
from tchannel.errors import ProtocolError


@pytest.mark.gen_test
@pytest.mark.call
def test_void():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testVoid(request, response, proxy):
        pass

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testVoid())

    assert resp.headers == {}
    assert resp.body is None


@pytest.mark.gen_test
@pytest.mark.call
def test_string():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_byte():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_i32():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_i64():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_double():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_binary():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_struct():

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


@pytest.mark.gen_test
@pytest.mark.call
def test_struct_with_headers():

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


@pytest.mark.gen_test
@pytest.mark.call
def test_nest():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_map():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_string_map():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_set():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_list():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_enum():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_type_def():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_map_map():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_insanity():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_multi():
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_exception():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testException(request, response, proxy):

        if request.args.arg == 'Xception':
            raise ThriftTest.Xception(
                errorCode=1001,
                message=request.args.arg
            )
        elif request.args.arg == 'TException':
            # TODO - what to raise here? We dont want dep on Thrift
            # so we don't have thrift.TException available to us...
            raise Exception()

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='service',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    # case #1
    with pytest.raises(ThriftTest.Xception) as e:
        yield tchannel.thrift(
            service.testException(arg='Xception')
        )
        assert e.value.errorCode == 1001
        assert e.value.message == 'Xception'

    # case #2
    with pytest.raises(ProtocolError):
        yield tchannel.thrift(
            service.testException(arg='TException')
        )

    # case #3
    resp = yield tchannel.thrift(
        service.testException(arg='something else')
    )
    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body is None


@pytest.mark.gen_test
@pytest.mark.call
def test_multi_exception():

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

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='service',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    # case #1
    with pytest.raises(ThriftTest.Xception) as e:
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception', arg1='thingy')
        )
        assert e.value.errorCode == 1001
        assert e.value.message == 'This is an Xception'

    # case #2
    with pytest.raises(ThriftTest.Xception2) as e:
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception2', arg1='thingy')
        )
        assert e.value.errorCode == 2002

    # case #3
    resp = yield tchannel.thrift(
        service.testMultiException(arg0='something else', arg1='thingy')
    )
    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body == ThriftTest.Xtruct('thingy')


@pytest.mark.gen_test
@pytest.mark.call
def test_oneway():
    # this is currently unsupported
    pass


@pytest.mark.gen_test
@pytest.mark.call
def test_call_response_should_contain_transport_headers():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testString(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testString('hi'))

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body == 'hi'

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.THRIFT
    assert resp.transport.failure_domain is None


@pytest.mark.gen_test
@pytest.mark.call
def test_call_unexpected_error_should_result_in_protocol_error():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testMultiException(request, response, proxy):
        raise Exception('well, this is unfortunate')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    with pytest.raises(ProtocolError):
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception', arg1='thingy')
        )
