from __future__ import absolute_import

import pytest

from tchannel import TChannel, Request
from tchannel.errors import BadRequestError
from tchannel.testing.dispatch import handle


@pytest.fixture
def server():
    tchannel = TChannel('test_server')

    @tchannel.raw.register
    def hello(request):
        return request.body + " world"

    return tchannel


@pytest.mark.gen_test
def test_handle_success(server):
    request = Request(
        body="hello",
        endpoint="hello",
    )
    response = yield handle(server, request)
    assert response.body == request.body + " world"


@pytest.mark.gen_test
def test_handle_unknown_endpoint(server):
    request = Request(
        body="hello",
        endpoint="xxxxx",
    )

    with pytest.raises(BadRequestError):
        yield handle(server, request)
