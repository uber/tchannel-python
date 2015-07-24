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

from tchannel.testing.vcr.types import Request, Response
from tchannel.testing.vcr.cassette import Cassette
from tchannel.testing.vcr.exceptions import (
    RequestNotFoundError,
    UnsupportedVersionError,
)


def test_path_does_not_exist(tmpdir):
    cass = Cassette(str(tmpdir.join('data.yaml')))
    assert len(cass.data) == 0


def test_save_without_recording(tmpdir):
    path = tmpdir.join('data.yaml')

    cass = Cassette(str(path))
    cass.save()

    assert not path.check()


def test_save_and_replay(tmpdir):
    path = tmpdir.join('data.yaml')
    cass = Cassette(str(path))

    request = Request('foo', 'bar', '', 'body')
    response = Response(0, '', 'response body')

    cass.record(request, response)

    # Can't replay until saved.
    assert not cass.can_replay(request)

    cass.save()
    cass = Cassette(str(path))

    assert cass.can_replay(request)
    assert cass.replay(request) == response
    assert cass.play_count == 1

    with pytest.raises(RequestNotFoundError):
        # a single request can only be played once in a given session.
        cass.replay(request)


def test_replay_unknown(tmpdir):
    path = tmpdir.join('data.yaml')
    cass = Cassette(str(path))

    cass.record(Request('foo', 'bar', '', 'body'), Response(0, '', 'resp'))
    cass.save()

    request = Request('another', 'method', '', 'body')

    assert not cass.can_replay(request)
    with pytest.raises(RequestNotFoundError):
        cass.replay(request)


def test_record_same(tmpdir):
    path = tmpdir.join('data.yaml')
    cass = Cassette(str(path))

    request = Request('foo', 'bar', '', 'body')
    response1 = Response(0, '', 'resp')
    response2 = Response(1, '', 'two')

    cass.record(request, response1)
    cass.record(request, response2)
    cass.save()

    cass = Cassette(str(path))

    assert cass.replay(request) == response1
    assert cass.replay(request) == response2
    assert cass.play_count == 2


def test_unsupported_version(tmpdir):
    path = tmpdir.join('data.yaml')
    path.write(
        '\n'.join([
            'interactions:',
            '- request:',
            '    body: request body',
            '    endpoint: foo',
            '    headers: headers',
            '    service: bar',
            '  response:',
            '    body: response body',
            '    headers: headers',
            '    status: 0',
            'version: 2',
        ])
    )

    with pytest.raises(UnsupportedVersionError):
        Cassette(str(path))
