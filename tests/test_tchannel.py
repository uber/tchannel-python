from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel, Response, formats


@pytest.mark.call
def test_should_get_default_formatters():

    tchannel = TChannel(name='test')

    for f in formats.DEFAULT_FORMATS:
        format = getattr(tchannel, f.name)
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

    response = yield tchannel.call(
        format=formats.RAW,
        service=mock_server.hostport,
        endpoint=endpoint,
        body=body
    )

    assert isinstance(response, Response)
    assert response.body == body


@pytest.mark.gen_test
@pytest.mark.call
def test_raw_call_should_get_response(mock_server):

    endpoint = 'endpoint'
    body = 'body'

    mock_server.expect_call(endpoint).and_write(
        headers=endpoint, body=body
    )

    tchannel = TChannel(name='test')

    response = yield tchannel.raw.call(
        service=mock_server.hostport,
        endpoint=endpoint,
        body=body
    )

    assert isinstance(response, Response)
    assert response.body == body
