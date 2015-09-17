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

from tchannel import TChannel, thrift
from tchannel.health import Meta
from tchannel.health import HealthStatus


@pytest.mark.gen_test
def test_default_health():
    server = TChannel("health_test_server")
    server.listen()

    client = TChannel("health_test_client")

    service = thrift.load(
        path='tchannel/health/meta.thrift',
        service='health_test_server',
        hostport=server.hostport,
    )

    resp = yield client.thrift(service.Meta.health())
    assert resp.body.ok is True
    assert resp.body.message is None


@pytest.mark.gen_test
def test_user_health():
    server = TChannel("health_test_server")

    @server.thrift.register(Meta, method="health")
    def user_health(request):
        return HealthStatus(ok=False, message="from me")

    server.listen()

    client = TChannel("health_test_client")
    service = thrift.load(
        path='tchannel/health/meta.thrift',
        service='health_test_server',
        hostport=server.hostport,
    )

    resp = yield client.thrift(service.Meta.health())
    assert resp.body.ok is False
    assert resp.body.message == "from me"
