from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel, formats
from tchannel import response


@pytest.mark.call
def test_should_get_default_formatters():

    tchannel = TChannel(name='test')

    for f in formats.DEFAULT_FORMATS:
        format = getattr(tchannel, f.NAME)
        assert format, "default format not found"
        assert isinstance(format, f)


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response(mock_server):

    endpoint = 'endpoint'
    body = 'body'

    mock_server.expect_call(endpoint).and_write(
        headers=endpoint, body=body
    )

    tchannel = TChannel(name='test')

    resp = yield tchannel.call(
        format=formats.RAW,
        service=mock_server.hostport,
        arg1=endpoint,
        arg2=None,
        arg3=body
    )

    # verify body
    assert isinstance(resp, response.Response)
    assert resp.body == body

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.format == formats.RAW
    assert resp.transport.failure_domain is None
