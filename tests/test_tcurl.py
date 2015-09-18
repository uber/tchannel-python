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

import collections

import mock
import pytest

from tchannel.tcurl import parse_args


Expectation = collections.namedtuple(
    'Expectation',
    'host, service, headers, endpoint, body, thrift, json',
)


@pytest.mark.parametrize('input, expectations', [
    (   # basic case
        ['-p', 'localhost:54496', '-s', 'larry', '--headers', '{"req": "header"}', '--body', '{"req": "body"}', '--json', '--endpoint', 'foo'],
        dict(host='localhost:54496', headers={'req': 'header'}, body={"req": "body"}, json=True)
    ),
    (
        ['--service', 'larry', '--thrift', 'tests/data/idls/ThriftTest.thrift', '--endpoint', 'foo::bar'],
        dict(service="larry", thrift=mock.ANY, endpoint='foo::bar'),
    ),
])
def test_parse_valid_args(input, expectations):
    args = parse_args(input)

    for key, expected in expectations.iteritems():
        assert expected == getattr(args, key)


@pytest.mark.parametrize('input, message', [
    (
        [''],
        'argument --service/-s is required'
    ),
    (
        ['--service', 'larry', '--thrift'],
        '--thrift/-t: expected one argument',
    ),
    (
        ['--service', 'larry', '--thrift', 'foo.thrift'],
        'No such file or directory',
    ),
    (
        ['--service', 'larry', '--thrift', 'tests/data/idls/ThriftTest.thrift', '--endpoint'],
        '--endpoint/-1: expected one argument',
    ),
    (
        ['--service', 'larry', '--thrift', 'tests/data/idls/ThriftTest.thrift', '--endpoint', 'foo'],
        '--endpoint should be of the form'
    ),
    (
        ['-p', 'localhost:54496', '-s', 'larry', '--headers', '{"req": "header"}', '--body', '{"req": "body"}', '--json'],
        '--json must be used with --endpoint',
    )
])
def test_parse_invalid_args(input, message, capsys):
    with pytest.raises(SystemExit) as e:
        parse_args(input)

    # Arg parse always dies with an error code of 2.
    assert e.value.message == 2

    out, err = capsys.readouterr()
    assert message in err
