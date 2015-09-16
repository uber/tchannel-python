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
from tchannel.event import EventHook
from tchannel.tornado.peer import PeerState
import tornado
import tornado.gen
from mock import patch

from tchannel import retry
from tchannel.errors import BusyError
from tchannel.errors import TChannelError
from tchannel.errors import TimeoutError
from tchannel.messages import ErrorCode
from tchannel.tornado import Request
from tchannel.tornado import TChannel
from tchannel.tornado.stream import InMemStream


@tornado.gen.coroutine
def handler_error(request, response):
    yield tornado.gen.sleep(0.01)
    response.connection.send_error(
        ErrorCode.busy,
        "retry",
        response.id,
    )
    # stop normal response streams
    response.set_exception(TChannelError("stop stream"))


@tornado.gen.coroutine
def handler_success(request, response):
    response.set_body_s(InMemStream("success"))


def server(endpoint):
    tchannel_server = TChannel(name='testserver', hostport='localhost:0')
    tchannel_server.register(endpoint, 'raw', handler_error)
    tchannel_server.listen()
    return tchannel_server


class FakeState(PeerState):
    def score(self):
        return 100


def chain(number_of_peers, endpoint):
    tchannel = TChannel(name='test')
    for i in range(number_of_peers):
        p = tchannel.peer_group.get(server(endpoint).hostport)
        # Gaurantee error servers have score in order to pick first.
        p.state = FakeState()

    return tchannel


@pytest.mark.gen_test
def test_retry_timeout():
    endpoint = b'tchannelretrytest'
    tchannel = chain(3, endpoint)
    with (
        patch(
            'tchannel.tornado.Request.should_retry_on_error',
            autospec=True)
    ) as mock_should_retry_on_error:
        mock_should_retry_on_error.return_value = True
        with pytest.raises(TimeoutError):
            yield tchannel.request(
                score_threshold=0,
            ).send(
                endpoint,
                "test",
                "test",
                headers={
                    're': retry.CONNECTION_ERROR_AND_TIMEOUT
                },
                ttl=0.005,
                retry_limit=2,
            )


@pytest.mark.gen_test
def test_retry_on_error_fail():
    endpoint = b'tchannelretrytest'
    tchannel = chain(3, endpoint)

    with (
        patch(
            'tchannel.tornado.Request.should_retry_on_error',
            autospec=True
        )
    ) as mock_should_retry_on_error:
        mock_should_retry_on_error.return_value = True
        with pytest.raises(BusyError) as e:
            yield tchannel.request(
                score_threshold=0
            ).send(
                endpoint,
                "test",
                "test",
                headers={
                    're': retry.CONNECTION_ERROR_AND_TIMEOUT
                },
                ttl=0.02,
                retry_limit=2,
            )

        assert mock_should_retry_on_error.called
        assert mock_should_retry_on_error.call_count == 3
        assert e.value.code == ErrorCode.busy


class MyTestHook(EventHook):
    def __init__(self):
        self.received_response = 0
        self.received_error = 0

    def after_receive_response(self, request, response):
        self.received_response += 1
        assert request.id == response.id

    def after_receive_error(self, request, error):
        self.received_error += 1
        assert request.id == error.id


@pytest.mark.gen_test
def test_retry_on_error_success():
    endpoint = b'tchannelretrytest'
    tchannel = chain(2, endpoint)
    hook = MyTestHook()
    tchannel.hooks.register(hook)

    tchannel_success = TChannel(name='test', hostport='localhost:0')
    tchannel_success.register(endpoint, 'raw', handler_success)
    tchannel_success.listen()
    tchannel.peer_group.get(tchannel_success.hostport)

    with (
        patch(
            'tchannel.tornado.Request.should_retry_on_error',
            autospec=True)
    ) as mock_should_retry_on_error:
        mock_should_retry_on_error.return_value = True
        response = yield tchannel.request(
            score_threshold=0
        ).send(
            endpoint,
            "test",
            "test",
            headers={
                're': retry.CONNECTION_ERROR_AND_TIMEOUT,
            },
            ttl=1,
            retry_limit=2,
        )

        header = yield response.get_header()
        body = yield response.get_body()
        assert body == "success"
        assert header == ""

    assert hook.received_response == 1
    assert hook.received_error == 2


@pytest.mark.gen_test
@pytest.mark.parametrize('retry_flag, error_code, result', [
    (retry.CONNECTION_ERROR, ErrorCode.busy, True),
    (retry.CONNECTION_ERROR, ErrorCode.declined, True),
    (retry.CONNECTION_ERROR, ErrorCode.timeout, False),
    (retry.CONNECTION_ERROR_AND_TIMEOUT, ErrorCode.timeout, True),
    (retry.TIMEOUT, ErrorCode.unexpected, False),
    (retry.TIMEOUT, ErrorCode.network_error, False),
    (retry.CONNECTION_ERROR, ErrorCode.network_error, True),
    (retry.NEVER, ErrorCode.network_error, False),
    (retry.CONNECTION_ERROR_AND_TIMEOUT, ErrorCode.cancelled, False),
    (retry.CONNECTION_ERROR_AND_TIMEOUT, ErrorCode.bad_request, False),
    (retry.CONNECTION_ERROR, ErrorCode.fatal, True),
    (retry.TIMEOUT, ErrorCode.fatal, False),
    (retry.TIMEOUT, ErrorCode.unhealthy, False),
    (retry.CONNECTION_ERROR_AND_TIMEOUT, ErrorCode.unhealthy, False),
],
    ids=lambda arg: str(arg)
)
def test_should_retry_on_error(retry_flag, error_code, result):
    request = Request(
        headers={'re': retry_flag},
    )

    error = TChannelError.from_code(error_code, description="retry")
    assert request.should_retry_on_error(error) == result
