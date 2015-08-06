from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
from tornado import gen

from tchannel import (
    TChannel, from_thrift_module,
    schemes, response
)
from tchannel.errors import OneWayNotSupportedError
from tchannel.tornado import TChannel as DeprecatedTChannel
from tchannel.thrift import client_for
from tests.data.generated.ThriftTest import ThriftTest, SecondService
from tchannel.errors import ProtocolError


# TODO - where possible, in req/res style test, create parameterized tests,
#        each test should test w headers and wout
#        and potentially w retry and timeout as well.
#        note this wont work with complex scenarios

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
def test_void_with_headers():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testVoid(request, response, proxy):
        response.write_header('resp', 'header')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testVoid())

    assert resp.headers == {
        'resp': 'header'
    }
    assert resp.body is None


@pytest.mark.gen_test
@pytest.mark.call
def test_string():

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

    resp = yield tchannel.thrift(
        service.testString('howdy')
    )

    assert resp.headers == {}
    assert resp.body == 'howdy'


@pytest.mark.gen_test
@pytest.mark.call
def test_byte():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testByte(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(
        service.testByte(63)
    )

    assert resp.headers == {}
    assert resp.body == 63


@pytest.mark.gen_test
@pytest.mark.call
def test_i32():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testI32(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    # case #1
    resp = yield tchannel.thrift(
        service.testI32(-1)
    )
    assert resp.headers == {}
    assert resp.body == -1

    # case #2
    resp = yield tchannel.thrift(
        service.testI32(1)
    )
    assert resp.headers == {}
    assert resp.body == 1


@pytest.mark.gen_test
@pytest.mark.call
def test_i64():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testI64(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(
        service.testI64(-34359738368)
    )

    assert resp.headers == {}
    assert resp.body == -34359738368


@pytest.mark.gen_test
@pytest.mark.call
def test_double():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testDouble(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(
        service.testDouble(-5.235098235)
    )

    assert resp.headers == {}
    assert resp.body == -5.235098235


@pytest.mark.gen_test
@pytest.mark.call
def test_binary():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testBinary(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(
        service.testBinary(
            # this is ThriftTest.Xtruct(string_thing='hi')
            '\x0c\x00\x00\x0b\x00\x01\x00\x00\x00\x0bhi\x00\x00'
        )
    )

    assert resp.headers == {}
    assert (
        resp.body ==
        '\x0c\x00\x00\x0b\x00\x01\x00\x00\x00\x0bhi\x00\x00'
    )


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

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testNest(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    xstruct = ThriftTest.Xtruct(
        string_thing='hi',
        byte_thing=1,
        i32_thing=-1,
        i64_thing=-34359738368,
    )
    xstruct2 = ThriftTest.Xtruct2(
        byte_thing=1,
        struct_thing=xstruct,
        i32_thing=1,
    )

    resp = yield tchannel.thrift(
        service.testNest(thing=xstruct2)
    )

    assert resp.headers == {}
    assert resp.body == xstruct2


@pytest.mark.gen_test
@pytest.mark.call
def test_map():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testMap(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )
    x = {
        0: 1,
        1: 2,
        2: 3,
        3: 4,
        -1: -2,
    }

    resp = yield tchannel.thrift(
        service.testMap(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_string_map():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testStringMap(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )
    x = {
        'hello': 'there',
        'my': 'name',
        'is': 'shirly',
    }

    resp = yield tchannel.thrift(
        service.testStringMap(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_set():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testSet(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )
    x = set([8, 1, 42])

    resp = yield tchannel.thrift(
        service.testSet(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_list():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testList(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )
    x = [1, 4, 9, -42]

    resp = yield tchannel.thrift(
        service.testList(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_enum():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testEnum(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )
    x = ThriftTest.Numberz.FIVE

    resp = yield tchannel.thrift(
        service.testEnum(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_type_def():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testTypedef(request, response, proxy):
        return request.args.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )
    x = 0xffffffffffffff  # 7 bytes of 0xff

    resp = yield tchannel.thrift(
        service.testTypedef(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_map_map():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    map_map = {
        -4: {
            -4: -4,
            -3: -3,
            -2: -2,
            -1: -1,
        },
        4: {
            1: 1,
            2: 2,
            3: 3,
            4: 4,
        },
    }

    @server.register(ThriftTest)
    def testMapMap(request, response, proxy):
        return map_map

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(
        service.testMapMap(1)
    )

    assert resp.headers == {}
    assert resp.body == map_map


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

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    # TODO - server should raise same exception as client
    with pytest.raises(AssertionError):
        @server.register(ThriftTest)
        def testOneway(request, response, proxy):
            pass

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    with pytest.raises(OneWayNotSupportedError):
        yield tchannel.thrift(service.testOneway(1))


@pytest.mark.gen_test
@pytest.mark.call
def test_second_service_blah_blah():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testString(request, response, proxy):
        return request.args.thing

    @server.register(SecondService)
    def blahBlah(request, response, proxy):
        pass

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    second_service = from_thrift_module(
        service='server',
        thrift_module=SecondService,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testString('thing'))

    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body == 'thing'

    resp = yield tchannel.thrift(second_service.blahBlah())

    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body is None


@pytest.mark.gen_test
@pytest.mark.call
def test_second_service_second_test_string():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register(ThriftTest)
    def testString(request, response, proxy):
        return request.args.thing

    @server.register(SecondService)
    @gen.coroutine
    def secondtestString(request, response, proxy):

        # TODO - is this really how our server thrift story looks?
        ThriftTestService = client_for(
            service='server',
            service_module=ThriftTest
        )
        service = ThriftTestService(
            tchannel=proxy,
            hostport=server.hostport,
        )

        resp = yield service.testString(request.args.thing)

        response.write_result(resp)

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = from_thrift_module(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    second_service = from_thrift_module(
        service='server',
        thrift_module=SecondService,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testString('thing'))

    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body == 'thing'

    resp = yield tchannel.thrift(
        second_service.secondtestString('second_string')
    )

    assert isinstance(resp, response.Response)
    assert resp.headers == {}
    assert resp.body == 'second_string'


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
