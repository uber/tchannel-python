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
import mock

import pytest

from tchannel import messages
from tchannel import TChannel
from tchannel import thrift
from tchannel.errors import FatalProtocolError
from tchannel.io import BytesIO
from tchannel.messages import CallRequestMessage
from tchannel.messages import ChecksumType
from tchannel.messages.common import generate_checksum
from tchannel.messages.common import verify_checksum


@pytest.mark.parametrize('checksum_type', [
    (ChecksumType.none),
    (ChecksumType.crc32),
    (ChecksumType.crc32c),
])
def test_checksum(checksum_type):
    message = CallRequestMessage()
    message.checksum = (checksum_type, None)
    generate_checksum(message)
    payload = messages.RW[message.message_type].write(
        message, BytesIO()
    ).getvalue()

    msg = messages.RW[message.message_type].read(BytesIO(payload))
    assert verify_checksum(msg)


@pytest.mark.gen_test
def test_default_checksum_type():
    server = TChannel("server")
    server.listen()
    with mock.patch(
        'tchannel.messages.common.compute_checksum', autospec=True,
    ) as mock_compute_checksum:
        client = TChannel("client")
        service = thrift.load(
            path='tchannel/health/meta.thrift',
            service='health_test_server',
            hostport=server.hostport,
        )
        with pytest.raises(FatalProtocolError):
            yield client.thrift(service.Meta.health())

        mock_compute_checksum.assert_called_with(
            ChecksumType.crc32c, mock.ANY, mock.ANY,
        )
