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
from tornado import concurrent

from tchannel import (
    TChannel,
    Request,
    Response,
    thrift,
    thrift_request_builder,
    schemes,
)
from tchannel.response import TransportHeaders
from tchannel.errors import OneWayNotSupportedError
from tchannel.errors import UnexpectedError
from tchannel.errors import ValueExpectedError
from tchannel.sync import TChannel as SyncTChannel
from tchannel.sync.thrift import client_for as sync_client_for
from tchannel.thrift import client_for
from tchannel.tornado import TChannel as DeprecatedTChannel

from tests.data.generated.ThriftTest import (
    SecondService as _SecondService,
    ThriftTest as _ThriftTest,
    ttypes as _ttypes,
)

from tchannel.tornado.connection import TornadoConnection
from tchannel.messages.call_request import CallRequestMessage


# TODO - where possible, in req/res style test, create parameterized tests,
#        each test should test w headers and wout
#        and potentially w retry and timeout as well.
#        note this wont work with complex scenarios


@pytest.fixture
def server(io_loop):  # need io_loop fixture for listen() to work
    server = TChannel(name='server')
    server.listen()
    return server


@pytest.fixture(params=[False, True], ids=['server_thrift', 'server_thriftrw'])
def use_thriftrw_server(request):
    return request.param


@pytest.fixture(params=[False, True], ids=['client_thrift', 'client_thriftrw'])
def use_thriftrw_client(request):
    return request.param


@pytest.fixture
def ThriftTest(use_thriftrw_server):
    """Used by servers to register endpoints for ThriftTest."""

    if use_thriftrw_server:
        return thrift.load(
            'tests/data/idls/ThriftTest.thrift',
        ).ThriftTest
    else:
        return _ThriftTest


@pytest.fixture
def SecondService(use_thriftrw_server):
    """Used by servers to register endpoints for SecondService."""

    if use_thriftrw_server:
        return thrift.load(
            'tests/data/idls/ThriftTest.thrift',
        ).SecondService
    else:
        return _SecondService


@pytest.fixture
def server_ttypes(use_thriftrw_server):
    """Provides access to generated types for the server."""

    if use_thriftrw_server:
        return thrift.load(
            path='tests/data/idls/ThriftTest.thrift',
        )
    else:
        return _ttypes


@pytest.fixture
def client_ttypes(use_thriftrw_client):
    """Provides access to generated types for the server."""

    if use_thriftrw_client:
        return thrift.load(
            path='tests/data/idls/ThriftTest.thrift',
        )
    else:
        return _ttypes


@pytest.fixture
def service(server, use_thriftrw_client):
    """Used by clients to build requests to ThriftTest."""

    if use_thriftrw_client:
        return thrift.load(
            path='tests/data/idls/ThriftTest.thrift',
            service='server',
            hostport=server.hostport,
        ).ThriftTest
    else:
        return thrift_request_builder(
            service='server',
            thrift_module=_ThriftTest,
            hostport=server.hostport,
        )


@pytest.fixture
def second_service(server, use_thriftrw_client):
    """Used by clients to build requests to SecondService."""

    if use_thriftrw_client:
        return thrift.load(
            path='tests/data/idls/ThriftTest.thrift',
            service='server',
            hostport=server.hostport,
        ).SecondService
    else:
        return thrift_request_builder(
            service='server',
            thrift_module=_SecondService,
            hostport=server.hostport,
        )


@pytest.mark.gen_test
@pytest.mark.call
def test_void(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testVoid(request):
        pass

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(service.testVoid())

    assert resp.headers == {}
    assert resp.body is None


@pytest.mark.gen_test
def test_double_registration_with_a_coroutine_hanlder(
    server,
    service,
    ThriftTest
):
    """Registering twice should override the original.

    This is mostly testing that ``build_handler`` correctly passes on the
    function name.
    """

    @server.thrift.register(ThriftTest)
    @server.thrift.register(ThriftTest)
    def testVoid(request):
        pass

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testVoid(),
        headers={'req': 'header'},
    )

    assert resp


@pytest.mark.gen_test
@pytest.mark.call
def test_void_with_headers(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testVoid(request):
        assert request.headers == {'req': 'header'}
        return Response(headers={'resp': 'header'})

    # Make a call:

    tchannel = TChannel(name='client')

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
def test_string(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testString('howdy')
    )

    assert resp.headers == {}
    assert resp.body == 'howdy'


@pytest.mark.gen_test
@pytest.mark.call
def test_byte(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testByte(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testByte(63)
    )

    assert resp.headers == {}
    assert resp.body == 63


@pytest.mark.gen_test
@pytest.mark.call
def test_i32(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testI32(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

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
def test_i64(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testI64(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testI64(-34359738368)
    )

    assert resp.headers == {}
    assert resp.body == -34359738368


@pytest.mark.gen_test
@pytest.mark.call
def test_double(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testDouble(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testDouble(-5.235098235)
    )

    assert resp.headers == {}
    assert resp.body == -5.235098235


@pytest.mark.gen_test
@pytest.mark.call
def test_binary(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testBinary(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testBinary(
            # this is ThriftTest.Xtruct(string_thing='hi')
            b'\x0c\x00\x00\x0b\x00\x01\x00\x00\x00\x0bhi\x00\x00'
        )
    )

    assert resp.headers == {}
    assert (
        resp.body ==
        b'\x0c\x00\x00\x0b\x00\x01\x00\x00\x00\x0bhi\x00\x00'
    )


@pytest.mark.gen_test
@pytest.mark.call
def test_struct(server, service, ThriftTest, server_ttypes, client_ttypes):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testStruct(request):

        assert request.body.thing.string_thing == 'req string'

        return server_ttypes.Xtruct(
            string_thing="resp string"
        )

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testStruct(client_ttypes.Xtruct("req string"))
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == {}
    assert resp.body == client_ttypes.Xtruct("resp string")


@pytest.mark.gen_test
@pytest.mark.call
def test_struct_with_headers(
    server, service, ThriftTest, server_ttypes, client_ttypes
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testStruct(request):

        assert isinstance(request, Request)
        assert request.headers == {'req': 'header'}
        assert request.body.thing.string_thing == 'req string'

        return Response(
            server_ttypes.Xtruct(
                string_thing="resp string"
            ),
            headers={'resp': 'header'},
        )

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testStruct(client_ttypes.Xtruct("req string")),
        headers={'req': 'header'},
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == {'resp': 'header'}
    assert resp.body == client_ttypes.Xtruct("resp string")


@pytest.mark.gen_test
@pytest.mark.call
def test_nest(server, service, ThriftTest, client_ttypes):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testNest(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    xstruct = client_ttypes.Xtruct(
        string_thing='hi',
        byte_thing=1,
        i32_thing=-1,
        i64_thing=-34359738368,
    )
    xstruct2 = client_ttypes.Xtruct2(
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
def test_map(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testMap(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

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
def test_string_map(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testStringMap(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

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
def test_set(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testSet(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    x = set([8, 1, 42])

    resp = yield tchannel.thrift(
        service.testSet(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_list(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testList(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    x = [1, 4, 9, -42]

    resp = yield tchannel.thrift(
        service.testList(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_enum(server, service, ThriftTest, client_ttypes):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testEnum(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    x = client_ttypes.Numberz.FIVE

    resp = yield tchannel.thrift(
        service.testEnum(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_type_def(server, service, ThriftTest):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testTypedef(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

    x = 0xffffffffffffff  # 7 bytes of 0xff

    resp = yield tchannel.thrift(
        service.testTypedef(thing=x)
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_map_map(server, service, ThriftTest):

    # Given this test server:

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

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.thrift(
        service.testMapMap(1)
    )

    assert resp.headers == {}
    assert resp.body == map_map


@pytest.mark.gen_test
@pytest.mark.call
def test_insanity(server, service, ThriftTest, server_ttypes, client_ttypes):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testInsanity(request):
        result = {
            1: {
                2: request.body.argument,
                3: request.body.argument,
            },
            2: {
                6: server_ttypes.Insanity(),
            },
        }
        return result

    # Make a call:

    tchannel = TChannel(name='client')

    x = client_ttypes.Insanity(
        userMap={
            client_ttypes.Numberz.EIGHT: 0xffffffffffffff,
        },
        xtructs=[
            client_ttypes.Xtruct(
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
            6: client_ttypes.Insanity(),
        },
    }


@pytest.mark.gen_test
@pytest.mark.call
def test_multi(server, service, ThriftTest, server_ttypes, client_ttypes):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testMulti(request):
        return server_ttypes.Xtruct(
            string_thing='Hello2',
            byte_thing=request.body.arg0,
            i32_thing=request.body.arg1,
            i64_thing=request.body.arg2,
        )

    # Make a call:

    tchannel = TChannel(name='client')

    x = client_ttypes.Xtruct(
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
            arg4=client_ttypes.Numberz.FIVE,
            arg5=0xf0f0f0,
        )
    )

    assert resp.headers == {}
    assert resp.body == x


@pytest.mark.gen_test
@pytest.mark.call
def test_exception(server, service, ThriftTest, server_ttypes, client_ttypes):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testException(request):

        if request.body.arg == 'Xception':
            raise server_ttypes.Xception(
                errorCode=1001,
                message=request.body.arg
            )
        elif request.body.arg == 'TException':
            # TODO - what to raise here? We dont want dep on Thrift
            # so we don't have thrift.TException available to us...
            raise Exception()

    # Make a call:

    tchannel = TChannel(name='client')

    # case #1
    with pytest.raises(client_ttypes.Xception) as e:
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
def test_multi_exception(
    server, service, ThriftTest, server_ttypes, client_ttypes
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testMultiException(request):

        if request.body.arg0 == 'Xception':
            raise server_ttypes.Xception(
                errorCode=1001,
                message='This is an Xception',
            )
        elif request.body.arg0 == 'Xception2':
            raise server_ttypes.Xception2(
                errorCode=2002
            )

        return server_ttypes.Xtruct(string_thing=request.body.arg1)

    # Make a call:

    tchannel = TChannel(name='client')

    # case #1
    with pytest.raises(client_ttypes.Xception) as e:
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception', arg1='thingy')
        )
        assert e.value.errorCode == 1001
        assert e.value.message == 'This is an Xception'

    # case #2
    with pytest.raises(client_ttypes.Xception2) as e:
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
    assert resp.body == client_ttypes.Xtruct('thingy')


@pytest.mark.gen_test
@pytest.mark.call
def test_oneway(server, service, ThriftTest):

    # Given this test server:

    # TODO - server should raise same exception as client
    with pytest.raises(AssertionError):
        @server.thrift.register(ThriftTest)
        def testOneway(request):
            pass

    # Make a call:

    tchannel = TChannel(name='client')

    with pytest.raises(OneWayNotSupportedError):
        yield tchannel.thrift(service.testOneway(1))


@pytest.mark.gen_test
@pytest.mark.call
def test_second_service_blah_blah(
    server, service, second_service, ThriftTest, SecondService
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    @server.thrift.register(SecondService)
    def blahBlah(request):
        pass

    # Make a call:

    tchannel = TChannel(name='client')

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
def test_second_service_second_test_string(
    server, service, second_service, ThriftTest, SecondService
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    @server.thrift.register(SecondService)
    @gen.coroutine
    def secondtestString(request):
        service = thrift_request_builder(
            service='server',
            thrift_module=_ThriftTest,
            hostport=server.hostport,
        )
        resp = yield tchannel.thrift(
            service.testString(request.body.thing),
        )

        raise gen.Return(resp)

    # Make a call:

    tchannel = TChannel(name='client')

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
def test_call_response_should_contain_transport_headers(
    server, service, ThriftTest
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    # Make a call:

    tchannel = TChannel(name='client')

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
def test_call_unexpected_error_should_result_in_unexpected_error(
    server, service, ThriftTest
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testMultiException(request):
        raise Exception('well, this is unfortunate')

    # Make a call:

    tchannel = TChannel(name='client')

    with pytest.raises(UnexpectedError):
        yield tchannel.thrift(
            service.testMultiException(arg0='Xception', arg1='thingy')
        )


@pytest.mark.gen_test
@pytest.mark.call
def test_value_expected_but_none_returned_should_error(
    server, service, ThriftTest, use_thriftrw_server, use_thriftrw_client
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testString(request):
        pass

    # Make a call:

    tchannel = TChannel(name='client')

    if use_thriftrw_server:
        # With thirftrw the client only sees an unexpected error because
        # thriftrw always disallows None results for functions that return
        # values.
        exc = UnexpectedError
    else:
        # If server is using thrift, it will be able to return an invalid
        # response. thriftrw will fail with a TypeError on invalid values. For
        # thrift, we'll check manually and raise ValueExpectedError.
        if use_thriftrw_client:
            exc = TypeError
        else:
            exc = ValueExpectedError

    with pytest.raises(exc) as exc_info:
        yield tchannel.thrift(
            service.testString('no return!?')
        )

    if not use_thriftrw_server:
        if use_thriftrw_client:
            assert 'did not receive any values' in str(exc_info)
        else:
            assert 'Expected a value to be returned' in str(exc_info)
            assert 'ThriftTest::testString' in str(exc_info)


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
def test_headers_should_be_a_map_of_strings(headers, service):

    tchannel = TChannel('client')

    with pytest.raises(ValueError):
        yield tchannel.thrift(
            request=service.testString('howdy'),
            headers=headers,
        )


@pytest.mark.gen_test
@pytest.mark.call
@pytest.mark.parametrize('ClientTChannel', [TChannel, DeprecatedTChannel])
def test_client_for(ClientTChannel, server, ThriftTest):

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing.encode('rot13')

    tchannel = ClientTChannel(name='client')

    client = client_for('server', _ThriftTest)(
        tchannel=tchannel,
        hostport=server.hostport,
    )

    resp = yield client.testString(thing='foo')
    assert resp == 'sbb'


@pytest.mark.gen_test
@pytest.mark.call
def test_client_for_with_sync_tchannel(server, ThriftTest):

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing.encode('rot13')

    tchannel = SyncTChannel(name='client')

    client = sync_client_for('server', _ThriftTest)(
        tchannel=tchannel,
        hostport=server.hostport,
    )

    future = client.testString(thing='foo')

    assert not isinstance(future, concurrent.Future)

    # Our server is sharing our IO loop so let it handle the
    # request.
    while not future.done():
        yield gen.moment

    resp = future.result()

    assert resp == 'sbb'


@pytest.mark.gen_test
@pytest.mark.call
def test_client_for_with_sync_tchannel_and_injected_thread_loop(
    server,
    ThriftTest,
    loop,
):
    tchannel = SyncTChannel(name='client', threadloop=loop)

    client = sync_client_for('server', _ThriftTest)(
        tchannel=tchannel,
        hostport=server.hostport,
    )

    assert client.testString(thing='foo')


@pytest.mark.gen_test
@pytest.mark.call
def test_exception_status_code_is_set(server, ThriftTest, server_ttypes):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testException(request):
        raise server_ttypes.Xception(
            errorCode=1001,
            message=request.body.arg
        )

    # Make a call:

    conn = yield TornadoConnection.outgoing(server.hostport)
    res = yield conn.send(
        CallRequestMessage(
            service=b'service',
            headers={b'cn': b'client', b'as': b'thrift'},
            args=[
                b'ThriftTest::testException',
                b'',
                bytearray([
                    0x0B,        # type = string
                    0x00, 0x01,  # field ID 1

                    0x00, 0x00, 0x00, 0x00,  # empty string

                    0x00,  # STOP
                ]),
            ],
        )
    )

    assert 1 == res.status_code


##############################################################################
# Calling registered functions directly should be equivalent to calling them
# as if they weren't registered at all


def body(**kwargs):
    """Constructs fake Request objects.

    The ``_headers`` kwarg may be used to set the header on the Request
    object.
    """
    request = mock.Mock()
    for k, v in kwargs.items():
        setattr(request, k, v)
    return request


def test_void_call_directly(server, ThriftTest):

    @server.thrift.register(ThriftTest)
    def testVoid(request):
        pass

    resp = testVoid(Request())
    assert resp is None


def test_void_with_headers_call_directly(server, ThriftTest):

    @server.thrift.register(ThriftTest)
    def testVoid(request):
        assert request.headers == {'req': 'header'}
        return Response(headers={'resp': 'header'})

    resp = testVoid(Request(headers={'req': 'header'}))
    assert resp.headers == {'resp': 'header'}
    assert resp.body is None


def test_non_void_call_directly(server, ThriftTest):

    @server.thrift.register(ThriftTest)
    def testString(request):
        return request.body.thing

    resp = testString(Request(body=body(thing='howdy')))
    assert resp == 'howdy'


def test_non_void_with_headers_call_directly(
    server, service, ThriftTest, server_ttypes, client_ttypes
):

    # Given this test server:

    @server.thrift.register(ThriftTest)
    def testStruct(request):
        assert request.headers == {'req': 'header'}
        assert request.body.thing.string_thing == 'req string'

        return Response(
            server_ttypes.Xtruct(string_thing="resp string"),
            headers={'resp': 'header'},
        )

    resp = testStruct(
        Request(
            headers={'req': 'header'},
            body=body(thing=client_ttypes.Xtruct("req string")),
        )
    )

    assert isinstance(resp, Response)
    assert resp.headers == {'resp': 'header'}
    assert resp.body == server_ttypes.Xtruct("resp string")
