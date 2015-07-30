from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
import tornado

from tchannel import TChannel, formats
from tchannel import response
from tchannel.tornado import TChannel as DeprecatedTChannel


@pytest.mark.call
def test_should_get_default_formatters():

    tchannel = TChannel(name='test')

    for f in formats.DEFAULT_FORMATS:
        format = getattr(tchannel, f.NAME)
        assert format, "default format not found"
        assert isinstance(format, f)


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    # Given this test server:

    server = DeprecatedTChannel(name='server')

    @server.register('endpoint', formats.RAW)
    @tornado.gen.coroutine
    def endpoint(request, response, proxy):

        header = yield request.get_header()
        body = yield request.get_body()

        assert header == 'raw req header'
        assert body == 'raw req body'

        response.write_header('raw resp header')
        response.write_body('raw resp body')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='test')

    resp = yield tchannel.call(
        format=formats.RAW,
        service=server.hostport,
        arg1='endpoint',
        arg2='raw req header',
        arg3='raw req body'
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.header == 'raw resp header'
    assert resp.body == 'raw resp body'

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.format == formats.RAW
    assert resp.transport.failure_domain is None
