from __future__ import absolute_import

import pytest

from tchannel.errors import ProtocolError
from tchannel.thrift import client_for
from tchannel.tornado import TChannel
from tchannel.testing import vcr


@pytest.fixture
def call(mock_server):
    channel = TChannel('test-client')

    def f(endpoint, body, headers=None, service=None, scheme=None):
        return channel.request(
            hostport=mock_server.hostport,
            service=service,
            arg_scheme=scheme,
        ).send(endpoint, headers or '', body)

    return f


@pytest.fixture
def thrift_client(thrift_service, mock_server):
    return client_for('myservice', thrift_service)(
        tchannel=TChannel('thrift-client'),
        hostport=mock_server.hostport,
    )


@pytest.mark.gen_test
def test_record_success(tmpdir, mock_server, call):
    path = tmpdir.join('data.yaml')

    mock_server.expect_call('hello').and_write('world').once()

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service')
        assert 'world' == (yield response.get_body())

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service')
        assert 'world' == (yield response.get_body())

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_success_thrift(
    tmpdir, mock_server, thrift_service, thrift_client
):
    path = tmpdir.join('data.yaml')
    expected_item = thrift_service.Item(
        'foo', thrift_service.Value(stringValue='bar')
    )
    mock_server.expect_call(thrift_service, method='getItem').and_result(
        expected_item
    ).once()

    with vcr.use_cassette(str(path)) as cass:
        item = yield thrift_client.getItem('foo')
        assert item == expected_item

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        item = yield thrift_client.getItem('foo')
        assert item == expected_item

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_protocol_exception(tmpdir, mock_server, call):
    path = tmpdir.join('data.yaml')

    mock_server.expect_call('hello').and_raise(
        Exception('great sadness')
    ).once()

    with pytest.raises(ProtocolError):
        with vcr.use_cassette(str(path)):
            yield call('hello', 'world')

    assert not path.check()  # nothing should've been recorded


@pytest.mark.gen_test
def test_record_thrift_exception(
    tmpdir, mock_server, thrift_service, thrift_client
):
    path = tmpdir.join('data.yaml')

    mock_server.expect_call(thrift_service, method='getItem').and_raise(
        thrift_service.ItemDoesNotExist('foo')
    ).once()

    with vcr.use_cassette(str(path)) as cass:
        with pytest.raises(thrift_service.ItemDoesNotExist):
            yield thrift_client.getItem('foo')

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        with pytest.raises(thrift_service.ItemDoesNotExist):
            yield thrift_client.getItem('foo')

    assert cass.play_count == 1
