# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import mock
import pytest
from tornado import gen

from tchannel import (
    TChannel, Request, Response,
    thrift_request_builder, schemes,
)
from tchannel.response import TransportHeaders
from tchannel.errors import OneWayNotSupportedError
from tchannel.errors import UnexpectedError
from tchannel.errors import ValueExpectedError
from tchannel.thrift import client_for
from tchannel.testing.data.generated.ThriftTest import SecondService
from tchannel.testing.data.generated.ThriftTest import ThriftTest
from tchannel.tornado import TChannel as DeprecatedTChannel


# TODO - where possible, in req/res style test, create parameterized tests,
#        each test should test w headers and wout
#        and potentially w retry and timeout as well.
#        note this wont work with complex scenarios

@pytest.mark.gen_test
@pytest.mark.call
def test_void():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testVoid(request):
        pass

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testVoid(request):
        assert request.headers == {'req': 'header'}
        return Response(headers={'resp': 'header'})

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(
        service.testVoid(),
        headers={'req': 'header'},
    )

    assert resp.headers == {
        'resp': 'header'
    }
    assert resp.body is None


@pytest.mark.gen_test
@pytest.mark.call
def test_string():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testByte(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testI32(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testI64(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testDouble(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testBinary(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testStruct(request):

        assert request.body.thing.string_thing == 'req string'

        return ThriftTest.Xtruct(
            string_thing="resp string"
        )

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='service',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    resp = yield tchannel.thrift(
        service.testStruct(ThriftTest.Xtruct("req string"))
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body == ThriftTest.Xtruct("resp string")


@pytest.mark.gen_test
@pytest.mark.call
def test_struct_with_headers():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testStruct(request):

        assert isinstance(request, Request)
        assert request.headers == {'req': 'header'}
        assert request.body.thing.string_thing == 'req string'

        return Response(
            ThriftTest.Xtruct(
                string_thing="resp string"
            ),
            headers={'resp': 'header'},
        )

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='service',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    resp = yield tchannel.thrift(
        service.testStruct(ThriftTest.Xtruct("req string")),
        headers={'req': 'header'},
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == {'resp': 'header'}
    assert resp.body == ThriftTest.Xtruct("resp string")


@pytest.mark.gen_test
@pytest.mark.call
def test_nest():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testNest(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testMap(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testStringMap(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testSet(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testList(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testEnum(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testTypedef(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

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

    @server.thrift.register(ThriftTest)
    def testMapMap(request):
        return map_map

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testInsanity(request):
        result = {
            1: {
                2: request.body.argument,
                3: request.body.argument,
            },
            2: {
                6: ThriftTest.Insanity(),
            },
        }
        return result

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    x = ThriftTest.Insanity(
        userMap={
            ThriftTest.Numberz.EIGHT: 0xffffffffffffff,
        },
        xtructs=[
            ThriftTest.Xtruct(
                string_thing='Hello2',
                byte_thing=74,
                i32_thing=0xff00ff,
                i64_thing=-34359738368,
            ),
        ],
    )

    resp = yield tchannel.thrift(
        service.testInsanity(x)
    )

    assert resp.headers == {}
    assert resp.body == {
        1: {
            2: x,
            3: x,
        },
        2: {
            6: ThriftTest.Insanity(),
        },
    }


@pytest.mark.gen_test
@pytest.mark.call
def test_multi():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testMulti(request):
        return ThriftTest.Xtruct(
            string_thing='Hello2',
            byte_thing=request.body.arg0,
            i32_thing=request.body.arg1,
            i64_thing=request.body.arg2,
        )

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    x = ThriftTest.Xtruct(
        string_thing='Hello2',
        byte_thing=74,
        i32_thing=0xff00ff,
        i64_thing=0xffffffffd0d0,
    )

    resp = yield tchannel.thrift(
        service.testMulti(
            arg0=x.byte_thing,
            arg1=x.i32_thing,
            arg2=x.i64_thing,
            arg3={0: 'abc'},
            arg4=ThriftTest.Numberz.FIVE,
            arg5=0xf0f0f0,
        )
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_exception():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testException(request):

        if request.body.arg == 'Xception':
            raise ThriftTest.Xception(
                errorCode=1001,
                message=request.body.arg
            )
        elif request.body.arg == 'TException':
            # TODO - what to raise here? We dont want dep on Thrift
            # so we don't have thrift.TException available to us...
            raise Exception()

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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
    with pytest.raises(UnexpectedError):
        yield tchannel.thrift(
            service.testException(arg='TException')
        )

    # case #3
    resp = yield tchannel.thrift(
        service.testException(arg='something else')
    )
    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body is None


@pytest.mark.gen_test
@pytest.mark.call
def test_multi_exception():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testMultiException(request):

        if request.body.arg0 == 'Xception':
            raise ThriftTest.Xception(
                errorCode=1001,
                message='This is an Xception',
            )
        elif request.body.arg0 == 'Xception2':
            raise ThriftTest.Xception2(
                errorCode=2002
            )

        return ThriftTest.Xtruct(string_thing=request.body.arg1)

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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
    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body == ThriftTest.Xtruct('thingy')


@pytest.mark.gen_test
@pytest.mark.call
def test_oneway():

    # Given this test server:

    server = TChannel(name='server')

    # TODO - server should raise same exception as client
    with pytest.raises(AssertionError):
        @server.thrift.register(ThriftTest)
        def testOneway(request):
            pass

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
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

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    @server.thrift.register(SecondService)
    def blahBlah(request):
        pass

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    second_service = thrift_request_builder(
        service='server',
        thrift_module=SecondService,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testString('thing'))

    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body == 'thing'

    resp = yield tchannel.thrift(second_service.blahBlah())

    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body is None


@pytest.mark.gen_test
@pytest.mark.call
def test_second_service_second_test_string():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    @server.thrift.register(SecondService)
    @gen.coroutine
    def secondtestString(request):

        service = thrift_request_builder(
            service='server',
            thrift_module=ThriftTest,
            hostport=server.hostport,
        )
        resp = yield tchannel.thrift(
            service.testString(request.body.thing),
        )

        raise gen.Return(resp)

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport
    )

    second_service = thrift_request_builder(
        service='server',
        thrift_module=SecondService,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testString('thing'))

    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body == 'thing'

    resp = yield tchannel.thrift(
        second_service.secondtestString('second_string')
    )

    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body == 'second_string'


@pytest.mark.gen_test
@pytest.mark.call
def test_call_response_should_contain_transport_headers():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    resp = yield tchannel.thrift(service.testString('hi'))

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body == 'hi'

    # verify response transport headers
    assert isinstance(resp.transport, TransportHeaders)
    assert resp.transport.scheme == schemes.THRIFT
    assert resp.transport.failure_domain is None


@pytest.mark.gen_test
@pytest.mark.call
def test_call_unexpected_error_should_result_in_unexpected_error():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testMultiException(request):
        raise Exception('well, this is unfortunate')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    with pytest.raises(UnexpectedError):
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception', arg1='thingy')
        )


@pytest.mark.gen_test
@pytest.mark.call
def test_value_expected_but_none_returned_should_error():

    # Given this test server:

    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testString(request):
        pass

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    service = thrift_request_builder(
        service='server',
        thrift_module=ThriftTest,
        hostport=server.hostport,
    )

    with pytest.raises(ValueExpectedError):
        yield tchannel.thrift(
            service.testString('no return!?')
        )


@pytest.mark.gen_test
@pytest.mark.call
@pytest.mark.parametrize('headers', [
    {'key': 1},
    {1: 'value'},
    {'key': {'key': 'value'}},
    100,
    -100,
    .1,
    10 << 6,
    True,
    Exception(),
])
def test_headers_should_be_a_map_of_strings(headers):

    tchannel = TChannel('client')

    with pytest.raises(ValueError):
        yield tchannel.thrift(
            request=mock.MagicMock(),
            headers=headers,
        )


@pytest.mark.gen_test
@pytest.mark.call
@pytest.mark.parametrize('ClientTChannel', [TChannel, DeprecatedTChannel])
def test_client_for(ClientTChannel):
    server = TChannel(name='server')

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing.encode('rot13')

    server.listen()

    tchannel = ClientTChannel(name='client')

    client = client_for('server', ThriftTest)(
        tchannel=tchannel,
        hostport=server.hostport,
    )

    resp = yield client.testString(thing='foo')
    assert resp == 'sbb'
