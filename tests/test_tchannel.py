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
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import subprocess
import textwrap

import psutil
import pytest
import tornado

from tchannel import TChannel
from tchannel import response
from tchannel import schemes


# TODO - need integration tests for timeout and retries, use testing.vcr


@pytest.mark.call
def test_should_have_default_schemes():

    tchannel = TChannel(name='test')

    for f in schemes.DEFAULT_SCHEMES:
        scheme = getattr(tchannel, f.NAME)
        assert scheme, "default scheme not found"
        assert isinstance(scheme, f)


@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    # Given this test server:

    server = TChannel(name='server')

    @server.register('endpoint', schemes.RAW)
    @tornado.gen.coroutine
    def endpoint(request, response, proxy):

        headers = yield request.get_header()
        body = yield request.get_body()

        assert headers == 'raw req headers'
        assert body == 'raw req body'

        response.write_header('raw resp headers')
        response.write_body('raw resp body')

    server.listen()

    # Make a call:

    tchannel = TChannel(name='client')

    resp = yield tchannel.call(
        scheme=schemes.RAW,
        service='server',
        arg1='endpoint',
        arg2='raw req headers',
        arg3='raw req body',
        hostport=server.hostport,
    )

    # verify response
    assert isinstance(resp, response.Response)
    assert resp.headers == 'raw resp headers'
    assert resp.body == 'raw resp body'

    # verify response transport headers
    assert isinstance(resp.transport, response.ResponseTransportHeaders)
    assert resp.transport.scheme == schemes.RAW
    assert resp.transport.failure_domain is None


def test_uninitialized_tchannel_is_fork_safe_by_not_scheduling_any_futures():
    process = psutil.Popen(
        [
            'python',
            '-c',
            textwrap.dedent(
                """
                import os
                from tchannel import TChannel
                t = TChannel("app")
                os.fork()
                t.listen()
                """
            ),
        ],
        stderr=subprocess.PIPE,
    )

    try:
        stderr = process.stderr.read()
        ret = process.wait()
        assert ret == 0 and not stderr, stderr
    finally:
        if process.is_running():
            process.kill()
