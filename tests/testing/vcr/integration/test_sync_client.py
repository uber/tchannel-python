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

from tchannel.errors import UnexpectedError
from tchannel.sync import TChannel
from tchannel.thrift import thrift_request_builder
from tchannel.testing import vcr


@pytest.mark.gen_test
def test_record_success(tmpdir, mock_server):
    path = tmpdir.join('data.yaml')
    mock_server.expect_call('hello').and_write('world').once()

    client = TChannel('test')

    with vcr.use_cassette(str(path)) as cass:
        response = client.raw(
            'hello_service',
            'hello',
            'world',
            hostport=mock_server.hostport,
        ).result(timeout=1)

        assert 'world' == response.body

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        response = client.raw(
            'hello_service',
            'hello',
            'world',
            hostport=mock_server.hostport,
        ).result(timeout=1)
        assert 'world' == response.body

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_success_no_hostport(tmpdir, mock_server):
    path = tmpdir.join('data.yaml')
    mock_server.expect_call('hello').and_write('world').once()
    client = TChannel('test', known_peers=[mock_server.hostport])

    with vcr.use_cassette(str(path)) as cass:
        response = client.raw(
            'hello_service',
            'hello',
            'world',
        ).result(timeout=1)

        assert 'world' == response.body

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        response = client.raw(
            'hello_service',
            'hello',
            'world',
        ).result(timeout=1)
        assert 'world' == response.body

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_success_no_hostport_new_channels(tmpdir, mock_server):
    path = tmpdir.join('data.yaml')
    mock_server.expect_call('hello').and_write('world').once()

    with vcr.use_cassette(str(path)) as cass:
        client = TChannel('test', known_peers=[mock_server.hostport])
        response = client.raw(
            'hello_service',
            'hello',
            'world',
        ).result(timeout=1)

        assert 'world' == response.body

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        client = TChannel('test', known_peers=[mock_server.hostport])
        response = client.raw(
            'hello_service',
            'hello',
            'world',
        ).result(timeout=1)
        assert 'world' == response.body

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_success_new_channels(tmpdir, mock_server):
    path = tmpdir.join('data.yaml')
    mock_server.expect_call(
        'hello', scheme='json',
    ).and_write('world').once()

    with vcr.use_cassette(str(path)) as cass:
        client = TChannel('test')
        response = client.json(
            'hello_service',
            'hello',
            'world',
            hostport=mock_server.hostport,
        ).result(timeout=1)

        assert 'world' == response.body

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        client = TChannel('test')
        response = client.json(
            'hello_service',
            'hello',
            'world',
            hostport=mock_server.hostport,
        ).result(timeout=1)
        assert 'world' == response.body

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_success_thrift(tmpdir, thrift_service, mock_server):
    myservice = thrift_request_builder(
        'myservice', thrift_service, hostport=mock_server.hostport
    )

    path = tmpdir.join('data.yaml')
    expected_item = thrift_service.Item(
        'foo', thrift_service.Value(stringValue='bar')
    )
    mock_server.expect_call(thrift_service, method='getItem').and_result(
        expected_item
    ).once()

    client = TChannel('test')

    with vcr.use_cassette(str(path)) as cass:
        response = client.thrift(myservice.getItem('foo')).result(1)
        item = response.body
        assert item == expected_item

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        response = client.thrift(myservice.getItem('foo')).result(1)
        item = response.body
        assert item == expected_item

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_protocol_exception(tmpdir, mock_server):
    path = tmpdir.join('data.yaml')

    mock_server.expect_call('hello').and_raise(
        Exception('great sadness')
    ).once()

    with pytest.raises(UnexpectedError):
        with vcr.use_cassette(str(path)):
            client = TChannel('test')
            client.raw(
                'hello_service',
                'hello',
                'world',
                hostport=mock_server.hostport,
            ).result(1)

    assert not path.check()  # nothing should've been recorded


@pytest.mark.gen_test
def test_record_thrift_exception(tmpdir, mock_server, thrift_service):
    path = tmpdir.join('data.yaml')

    myservice = thrift_request_builder(
        'myservice', thrift_service, hostport=mock_server.hostport
    )

    mock_server.expect_call(thrift_service, method='getItem').and_raise(
        thrift_service.ItemDoesNotExist('foo')
    ).once()

    client = TChannel('test')

    with vcr.use_cassette(str(path)) as cass:
        with pytest.raises(thrift_service.ItemDoesNotExist):
            client.thrift(myservice.getItem('foo')).result(1)

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        with pytest.raises(thrift_service.ItemDoesNotExist):
            client.thrift(myservice.getItem('foo')).result(1)

    assert cass.play_count == 1
