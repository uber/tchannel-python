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

from tchannel.testing.vcr.cassette import Cassette
from tchannel.testing.vcr.exceptions import (
    VCRError,
    RequestNotFoundError,
    UnsupportedVersionError,
)
from tchannel.testing.vcr.record_modes import RecordMode

from .strategies import requests, responses


@pytest.fixture
def path(tmpdir):
    return tmpdir.join('data.yaml')


def test_path_does_not_exist(path):
    cass = Cassette(str(path))
    assert len(cass.data) == 0


def test_save_without_recording(path):
    cass = Cassette(str(path))
    cass.save()

    assert not path.check()


def test_record_mode_invalid(path):
    with pytest.raises(VCRError):
        Cassette(str(path), record_mode='not_valid')


def test_invalid_matcher(path):
    with pytest.raises(KeyError):
        Cassette(str(path), matchers=('serviceName', 'not a matcher'))


def test_empty_file(path):
    path.write('')
    cass = Cassette(str(path))
    assert len(cass.data) == 0


def test_save_and_replay(path):
    request = requests.example()
    response = responses.example()

    with Cassette(str(path)) as cass:
        cass.record(request, response)

        # Can't replay until saved.
        assert not cass.can_replay(request)

    with Cassette(str(path)) as cass:
        assert cass.can_replay(request)
        assert cass.replay(request) == response
        assert cass.play_count == 1

        with pytest.raises(RequestNotFoundError):
            # a single request can only be played once in a given session.
            cass.replay(request)


def test_replay_unknown(path):
    request = requests.example()

    with Cassette(str(path)) as cass:
        cass.record(requests.example(), responses.example())

        assert not cass.can_replay(request)
        with pytest.raises(RequestNotFoundError):
            cass.replay(request)


def test_record_into_nonexistent_directory(tmpdir):
    path = tmpdir.join('somedir/data.yaml')
    request = requests.example()
    response = responses.example()

    with Cassette(str(path)) as cass:
        cass.record(request, response)

    with Cassette(str(path)) as cass:
        assert cass.can_replay(request)
        assert cass.replay(request) == response


def test_record_same(path):
    request = requests.example()
    response1 = responses.example()
    response2 = responses.example()

    with Cassette(str(path)) as cass:
        cass.record(request, response1)
        cass.record(request, response2)

    with Cassette(str(path)) as cass:

        assert cass.replay(request) == response1
        assert cass.replay(request) == response2
        assert cass.play_count == 2


def test_does_not_forget_on_new_interactions(path):
    req1 = requests.example()
    res1 = responses.example()

    with Cassette(str(path)) as cass:
        cass.record(req1, res1)

    req2 = requests.example()
    res2 = responses.example()

    with Cassette(str(path), record_mode=RecordMode.NEW_EPISODES) as cass:
        cass.record(req2, res2)

    with Cassette(str(path)) as cass:
        assert res1 == cass.replay(req1)
        assert res2 == cass.replay(req2)


def test_unsupported_version(path):
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


def test_record_mode_none(path):
    req = requests.example()
    res = responses.example()

    with Cassette(str(path), record_mode=RecordMode.NONE) as cass:
        with pytest.raises(AssertionError):
            cass.record(req, res)

    # save and try again
    with Cassette(str(path)) as cass:
        cass.record(req, res)

    with Cassette(str(path), record_mode=RecordMode.NONE) as cass:
        assert res == cass.replay(req)


def test_record_mode_all(path):
    req = requests.example()
    res = responses.example()
    res2 = responses.example()

    with Cassette(str(path)) as cass:
        cass.record(req, res)

    with Cassette(str(path), record_mode=RecordMode.ALL) as cass:
        assert not cass.can_replay(req)
        with pytest.raises(AssertionError):
            cass.replay(req)

    with Cassette(str(path), record_mode=RecordMode.ALL) as cass:
        cass.record(req, res2)

    with Cassette(str(path)) as cass:
        assert res2 == cass.replay(req)
