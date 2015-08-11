from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest
import tornado

from tchannel import TChannel
from tchannel import response
from tchannel import schemes


# TODO - need integration tests for timeout and retries, use testing.vcr


@pytest.mark.call
def test_should_have_default_schemes():

    tchannel = TChannel(name='test')

    for f in schemes.DEFAULT_SCHEMES:
        scheme = getattr(tchannel, f.NAME)
        assert scheme, "default scheme not found"
        assert isinstance(scheme, f)


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    # Given this test server:

    server = TChannel(name='server')

    @server.register('endpoint', schemes.RAW)
    @tornado.gen.coroutine
    def endpoint(request, response, proxy):

        headers = yield request.get_header()
        body = yield request.get_body()

        assert headers == 'raw req headers'
        assert body == 'raw req body'

        response.write_header('raw resp headers')
        response.write_body('raw resp body')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.call(
        scheme=schemes.RAW,
        service='server',
        arg1='endpoint',
        arg2='raw req headers',
        arg3='raw req body',
        hostport=server.hostport,
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.headers == 'raw resp headers'
    assert resp.body == 'raw resp body'

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.RAW
    assert resp.transport.failure_domain is None
