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

from tchannel.serializer.json import JsonSerializer


@pytest.mark.parametrize('v1', [
    ({}),
    ({'a': 'd'}),
])
def test_header(v1):
    serializer = JsonSerializer()
    assert v1 == serializer.deserialize_header(
        serializer.serialize_header(v1)
    )


@pytest.mark.parametrize('v1, v2', [
    (True, 'true'),
    (False, 'false'),
    ({}, '{}'),
    ({'a': 'd'}, '{"a": "d"}'),
    (2, '2'),
    (None, 'null'),
])
def test_body(v1, v2):
    serializer = JsonSerializer()
    assert v2 == serializer.serialize_body(v1)
    assert v1 == serializer.deserialize_body(v2)


def test_exception():
    serializer = JsonSerializer()

    with pytest.raises(ValueError):
        serializer.deserialize_header('{sss')

    with pytest.raises(TypeError):
        serializer.serialize_body({"sss"})

    with pytest.raises(ValueError):
        serializer.deserialize_body('{sss')
