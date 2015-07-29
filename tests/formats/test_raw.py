from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel, Response, formats


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response(mock_server):

    endpoint = 'endpoint'
    body = 'body'

    mock_server.expect_call(endpoint).and_write(
        headers=endpoint, body=body
    )

    tchannel = TChannel(name='test')

    response = yield tchannel.raw(
        service=mock_server.hostport,
        endpoint=endpoint,
        body=body,
    )

    assert isinstance(response, Response)
    assert response.body == body
