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

import pytest

from tchannel import tcurl
from tchannel import TChannel
from tchannel.errors import NetworkError
from tchannel.errors import BadRequestError
from tchannel.tornado.connection import StreamConnection
from tests.util import big_arg


@pytest.mark.gen_test
def test_tornado_client_with_server_not_there():
    with pytest.raises(NetworkError):
        yield StreamConnection.outgoing(
            # Try a random port that we're not listening on.
            # This should fail.
            'localhost:41942'
        )


# TODO test case will fail due to StreamClosedError when
# increase the LARGE_AMOUNT to even bigger
@pytest.mark.gen_test
@pytest.mark.parametrize('arg2, arg3', [
    ("", big_arg()),
    (big_arg(), ""),
    ("test", big_arg()),
    (big_arg(),  "test"),
    (big_arg(), big_arg()),
    ("", ""),
    ("test", "test"),
],
    ids=lambda arg: str(len(arg))
)
def test_tchannel_call_request_fragment(mock_server,
                                        arg2, arg3):
    endpoint = b'tchannelpeertest'

    mock_server.expect_call(endpoint).and_write(
        headers=endpoint,
        body=arg3
    )

    tchannel = TChannel(name='test')

    response = yield tchannel.raw(
        service='test-service',
        hostport=mock_server.hostport,
        endpoint=endpoint,
        headers=arg2,
        body=arg3,
    )

    assert response.headers == endpoint
    assert response.body == arg3
    assert response.transport.scheme == 'raw'


@pytest.mark.gen_test
def test_tcurl(mock_server):
    endpoint = b'tcurltest'

    mock_server.expect_call(endpoint).and_write(
        headers=endpoint,
        body="hello"
    )

    hostport = 'localhost:%d' % mock_server.port
    response = yield tcurl.main([
        '--host', hostport,
        '--endpoint', endpoint,
        '--service', 'mock-server',
        '--raw',
    ])

    assert response.headers == endpoint
    assert response.body == "hello"


@pytest.mark.gen_test
def test_endpoint_not_found(mock_server):
    tchannel = TChannel(name='test')

    with pytest.raises(BadRequestError):
        yield tchannel.raw(
            service='test-server',
            endpoint='fooo',
            hostport=mock_server.hostport,
        )


@pytest.mark.gen_test
def test_connection_close(mock_server):
    tchannel = TChannel(name='test')

    # use a bad call to finish the hand shake and build the connection.
    with pytest.raises(BadRequestError):
        yield tchannel.raw(
            service='test-service',
            hostport=mock_server.hostport,
            endpoint='testg',
        )

    # close the server and close the connection.
    mock_server.tchannel._dep_tchannel.close()

    with pytest.raises(NetworkError):
        yield tchannel.raw(
            service='test-service',
            hostport=mock_server.hostport,
            endpoint='testg',
        )
