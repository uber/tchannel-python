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

from tchannel import thrift

from .mock_server import MockServer


class _MockConnection(object):
    def __init__(self):
        self.buff = bytearray()
        self.remote_host = "0.0.0.0"
        self.remote_host_port = "0"

    def write(self, payload, callback=None):
        self.buff.extend(payload)

    def getvalue(self):
        return self.buff

    def set_outbound_pending_change_callback(self, cb):
        pass

    def set_close_callback(self, cb):
        pass


@pytest.fixture
def connection():
    """Make a mock connection."""
    return _MockConnection()


@pytest.yield_fixture
def mock_server():
    with MockServer() as server:
        yield server


@pytest.fixture
def thrift_module(request):
    return thrift.load(
        'tests/data/idls//ThriftTest2.thrift', request.node.name
    )
