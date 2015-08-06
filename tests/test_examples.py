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

import pytest
import psutil


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
        while process.is_running() and not process.connections():
            pass

    try:
        yield process
    finally:
        process.kill()


@pytest.yield_fixture
def examples_dir():
    cwd = os.getcwd()

    examples = os.path.join(cwd, 'examples')

    assert os.path.exists(examples)

    try:
        os.chdir(examples)
        yield examples
    finally:
        os.chdir(cwd)


@pytest.mark.parametrize(
    'scheme, path',
    (
        ('raw', 'simple/raw/'),
        ('json', 'simple/json/'),
        # ('thrift', 'simple/thrift/'),
        ('guide', 'guide/keyvalue/keyvalue/'),
    )
)
def test_example(examples_dir, scheme, path):
    """Smoke test example code to ensure it still runs."""

    server_path = os.path.join(
        examples_dir,
        path + 'server.py',
    )

    client_path = os.path.join(
        examples_dir,
        path + 'client.py',
    )

    with popen(server_path, wait_for_listen=True):
        with popen(client_path) as client:

            out = client.stdout.read()

            # TODO the guide test should be the same as others
            if scheme == 'guide':
                assert out == 'Hello, world!\n'
                return

            body, headers = out.split(os.linesep)[:-1]

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

            elif scheme == 'thrift':

                headers = json.loads(headers)

                assert body == 'resp'
                assert headers == {
                    'resp': 'header',
                }
