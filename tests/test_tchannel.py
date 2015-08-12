from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import ipdb
import pytest
import tornado

from tchannel import TChannel, Response, schemes
from tchannel.response import ResponseTransportHeaders

# TODO - need integration tests for timeout and retries, use testing.vcr


@pytest.mark.call
def test_should_have_default_schemes():

    tchannel = TChannel(name='test')

    for f in schemes.DEFAULT_SCHEMES:
        scheme = getattr(tchannel, f.NAME)
        assert scheme, "default scheme not found"
        assert isinstance(scheme, f)


@pytest.mark.gen_test
@pytest.mark.callz
def test_call_should_get_response():

    # Given this test server:

    server = TChannel(name='server')

    @server.register(scheme=schemes.RAW)
    @tornado.gen.coroutine
    def endpoint(request):
        ipdb.set_trace()

        assert request.headers == 'raw req headers'
        assert request.body == 'raw req body'

        return Response('resp body', 'resp headers')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    ipdb.set_trace()

    resp = yield tchannel.call(
        scheme=schemes.RAW,
        service='server',
        arg1='endpoint',
        arg2='raw req headers',
        arg3='raw req body',
        hostport=server.hostport,
    )

    # verify response
    assert isinstance(resp, Response)
    assert resp.headers == 'raw resp headers'
    assert resp.body == 'raw resp body'

    # verify response transport headers
    assert isinstance(resp.transport, ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.RAW
    assert resp.transport.failure_domain is None
