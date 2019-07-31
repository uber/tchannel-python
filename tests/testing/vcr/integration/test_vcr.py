# Copyright (c) 2016 Uber Technologies, Inc.
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

import os
import pytest
from tornado import gen
from functools import partial

from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import InMemoryReporter

from tchannel.errors import UnexpectedError, TimeoutError
from tchannel.thrift import client_for
from tchannel.testing import vcr


@pytest.yield_fixture
def tracer():
    reporter = InMemoryReporter()
    tracer = Tracer(
        service_name='test-tracer',
        sampler=ConstSampler(True),
        reporter=reporter,
    )
    try:
        yield tracer
    finally:
        tracer.close()


@pytest.fixture(params=['old', 'new', 'new,tracing'])
def api(request):
    return request.param


@pytest.fixture
def use_old_api(api):
    return api == 'old'


@pytest.fixture
def trace_kwargs(api, tracer):
    kwargs = {}
    if 'tracing' in api.split(','):
        kwargs['trace'] = True
        kwargs['tracer'] = tracer
    return kwargs


@pytest.fixture
def get_body(use_old_api):
    if use_old_api:
        return (lambda r: r.get_body())
    else:
        @gen.coroutine
        def new_get_body(r):
            return r.body
        return new_get_body


@pytest.fixture
def call(mock_server, use_old_api, trace_kwargs):
    if use_old_api:
        from tchannel.tornado import TChannel

        channel = TChannel('test-client')

        def old_f(endpoint, body, headers=None, service=None, scheme=None,
                  ttl=None):
            return channel.request(
                hostport=mock_server.hostport,
                service=service,
                arg_scheme=scheme,
            ).send(endpoint, headers or '', body, ttl=ttl)

        return old_f
    else:
        from tchannel import TChannel
        channel = TChannel('test-client', **trace_kwargs)

        def new_f(endpoint, body, headers=None, service=None, scheme=None,
                  ttl=None):
            scheme = scheme or 'raw'
            return channel.call(
                hostport=mock_server.hostport,
                scheme=scheme,
                service=service,
                arg1=endpoint,
                arg2=headers or '',
                arg3=body,
                timeout=ttl,
            )

        return new_f


@pytest.fixture
def thrift_client(thrift_service, mock_server, use_old_api, trace_kwargs):
    if use_old_api:
        from tchannel.tornado import TChannel

        return client_for('myservice', thrift_service)(
            tchannel=TChannel('thrift-client'),
            hostport=mock_server.hostport,
        )
    else:
        from tchannel import TChannel
        from tchannel.thrift import thrift_request_builder

        myservice = thrift_request_builder(
            'myservice', thrift_service, hostport=mock_server.hostport
        )
        return mk_fake_client(
            TChannel('thrift-client', **trace_kwargs),
            myservice
        )


def mk_fake_client(channel, builder):

    class Client(object):

        @gen.coroutine
        def _call(self, name, *args, **kwargs):
            req = getattr(builder, name)(*args, **kwargs)
            res = yield channel.thrift(req)
            raise gen.Return(res.body)

        def __getattr__(self, name):
            return partial(self._call, name)

    return Client()


@pytest.mark.gen_test
def test_record_success(tmpdir, mock_server, call, get_body):
    path = tmpdir.join('data.yaml')

    mock_server.expect_call('hello').and_write('world').once()

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service')
        assert b'world' == (yield get_body(response))

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service')
        assert b'world' == (yield get_body(response))

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

    with pytest.raises(UnexpectedError):
        with vcr.use_cassette(str(path)):
            yield call('hello', 'world', service='hello_service')

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


@pytest.mark.gen_test
def test_use_cassette_as_decorator(tmpdir, mock_server, call, get_body):
    path = tmpdir.join('data.yaml')
    mock_server.expect_call('hello').and_write('world').once()

    @gen.coroutine
    @vcr.use_cassette(str(path))
    def f():
        response = yield call('hello', 'world', service='hello_service')
        body = yield get_body(response)
        raise gen.Return(body)

    body = yield f()
    assert body == b'world'

    body = yield f()
    assert body == b'world'


@pytest.mark.gen_test
def test_use_cassette_as_decorator_with_inject(tmpdir, mock_server, call):
    path = tmpdir.join('data.yaml')
    mock_server.expect_call('hello').and_raise(Exception('great sadness'))

    @gen.coroutine
    @vcr.use_cassette(str(path), inject=True)
    def f(cassette):
        with pytest.raises(UnexpectedError):
            yield call('hello', 'world', service='hello_service')

        assert len(cassette.data) == 0
        assert cassette.play_count == 0

    yield f()
    yield f()


@pytest.mark.gen_test
def test_use_cassette_with_matchers(tmpdir, mock_server, call, get_body):
    path = tmpdir.join('data.yaml')
    mock_server.expect_call('hello').and_write('world').once()

    with vcr.use_cassette(str(path), matchers=['body']) as cass:
        response = yield call('hello', 'world', service='hello_service')
        assert b'world' == (yield get_body(response))

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path), matchers=['body']) as cass:
        response = yield call(
            'not-hello', 'world', service='not_hello_service'
        )
        assert b'world' == (yield get_body(response))

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_into_nonexistent_directory(tmpdir, mock_server, call,
                                           get_body):
    path = tmpdir.join('somedir/data.yaml')

    mock_server.expect_call('hello').and_write('world').once()

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service')
        assert b'world' == (yield get_body(response))

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service')
        assert b'world' == (yield get_body(response))

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_success_with_ttl(tmpdir, mock_server, call, get_body):
    path = tmpdir.join('data.yaml')

    mock_server.expect_call('hello').and_write('world', delay=0.1).once()

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service',
                              ttl=0.2)
        assert b'world' == (yield get_body(response))

    assert cass.play_count == 0
    assert path.check(file=True)

    with vcr.use_cassette(str(path)) as cass:
        response = yield call('hello', 'world', service='hello_service',
                              ttl=0.05)  # shouldn't time out
        assert b'world' == (yield get_body(response))

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_record_success_with_ttl_timeout(tmpdir, mock_server, call, get_body):
    """Make sure legitimate request timeouts propagate during recording."""
    path = tmpdir.join('data.yaml')

    mock_server.expect_call('hello').and_write('world', delay=0.1).once()

    with pytest.raises(TimeoutError):
        with vcr.use_cassette(str(path)) as cass:
            response = yield call('hello', 'world', service='hello_service',
                                  ttl=0.05)
            assert b'world' == (yield get_body(response))

    assert cass.play_count == 0


@pytest.mark.gen_test
@pytest.mark.parametrize('tracing_before, tracing_after', [
    (True, True),
    (True, False),
    (False, True),
    (False, False),
], ids=['trace-trace', 'trace-notrace', 'notrace-trace', 'notrace-notrace'])
def test_vcr_with_tracing(
    tmpdir, mock_server, tracer, tracing_before, tracing_after
):
    from tchannel import TChannel

    mock_server.expect_call('hello', 'json').and_write('world').once()

    path = tmpdir.join('data.yaml')

    if tracing_before:
        ch = TChannel('client', trace=True, tracer=tracer)
    else:
        ch = TChannel('client')

    with vcr.use_cassette(str(path)) as cass:
        response = yield ch.json(
            hostport=mock_server.hostport,
            service='hello_service',
            endpoint='hello',
            body='world',
        )
        assert b'world' == response.body

    assert cass.play_count == 0
    assert path.check(file=True)

    if tracing_after:
        ch = TChannel('client', trace=True, tracer=tracer)
    else:
        ch = TChannel('client')

    with vcr.use_cassette(str(path), record_mode=vcr.RecordMode.NONE) as cass:
        response = yield ch.json(
            hostport=mock_server.hostport,
            service='hello_service',
            endpoint='hello',
            body='world',
        )
        assert b'world' == response.body

    assert cass.play_count == 1


@pytest.mark.gen_test
def test_old_recording_with_tracing(mock_server, tracer):
    from tchannel import TChannel

    # an existing recording that contains tracing information
    path = os.path.join(
        os.path.dirname(__file__), 'data', 'old_with_tracing.yaml'
    )
    ch = TChannel('client', trace=True, tracer=tracer)

    mock_server.expect_call('hello', 'json').and_write('world').once()
    with vcr.use_cassette(path, record_mode=vcr.RecordMode.NONE):
        response = yield ch.json(
            hostport=mock_server.hostport,
            service='hello_service',
            endpoint='hello',
            body='world',
        )
        assert b'world' == response.body


@pytest.mark.gen_test
def test_old_recording_without_tracing(mock_server, tracer):
    from tchannel import TChannel

    # an existing recording that does not contain tracing information
    path = os.path.join(
        os.path.dirname(__file__), 'data', 'old_without_tracing.yaml'
    )
    ch = TChannel('client', trace=True, tracer=tracer)

    mock_server.expect_call('hello', 'json').and_write('world').once()
    with vcr.use_cassette(path, record_mode=vcr.RecordMode.NONE):
        response = yield ch.json(
            hostport=mock_server.hostport,
            service='hello_service',
            endpoint='hello',
            body='world',
        )
        assert b'world' == response.body
