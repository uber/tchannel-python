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

from tchannel import TChannel
from tchannel import thrift


@pytest.fixture
def thrift_service():
    # TODO replace global thrift_service fixture that uses thrift --gen.
    return thrift.load(
        path='tests/data/idls/ThriftTest2.thrift',
        service='myservice',
    )


@pytest.mark.gen_test
def test_false_result(thrift_service):
    # Verify that we aren't treating False as None.

    app = TChannel(name='app')

    @app.thrift.register(thrift_service.Service)
    def healthy(request):
        return False

    app.listen()

    client = TChannel(name='client')
    response = yield client.thrift(
        thrift_service.Service.healthy(),
        hostport=app.hostport,
    )

    assert response.body is False
