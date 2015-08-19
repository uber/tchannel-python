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

import contextlib
import json
import os
import subprocess

import psutil
import pytest


@contextlib.contextmanager
def popen(path, wait_for_listen=False):
    process = psutil.Popen(
        ['python', path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if wait_for_listen:
        # It would be more correct to check ``conn.status ==
        # psutil.CONN_LISTEN`` but this works
        try:
            while process.is_running() and not process.connections():
                pass
        except psutil.Error:
            raise AssertionError(process.stderr.read())

    try:
        yield process
    finally:
        process.kill()


@pytest.mark.parametrize(
    'scheme, path',
    (
        ('raw', 'simple/raw/'),
        ('json', 'simple/json/'),
        ('thrift', 'simple/thrift/'),
        ('bench', 'benchmark/thrift/'),
        ('guide', 'guide/keyvalue/keyvalue/'),
    )
)
def test_example(scheme, path):
    """Smoke test example code to ensure it still runs."""

    server_path = os.path.join(
        'examples',
        path + 'server.py',
    )

    client_path = os.path.join(
        'examples',
        path + 'client.py',
    )

    with popen(server_path, wait_for_listen=True):
        with popen(client_path) as client:

            body = client.stdout.readline().strip()
            headers = client.stdout.readline().strip()

            # TODO the guide test should be the same as others
            if scheme == 'guide':
                assert body == 'Hello, world!'
                return

            if scheme == 'raw':

                assert body == 'resp body'
                assert headers == 'resp headers'

            elif scheme == 'json':

                body = json.loads(body)
                headers = json.loads(headers)

                assert body == {
                    'resp': 'body'
                }
                assert headers == {
                    'resp': 'header'
                }

            elif scheme == 'bench':
                assert int(body)
                assert int(headers)

            elif scheme == 'thrift':

                headers = json.loads(headers)

                assert body == 'resp'
                assert headers == {
                    'resp': 'header',
                }

            else:
                assert False
