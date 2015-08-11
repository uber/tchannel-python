from __future__ import absolute_import
import pytest

from tchannel.serializer.json import JsonSerializer


@pytest.mark.gen_test
@pytest.mark.parametrize('v1, v2', [
    (True, 'true'),
    (False, 'false'),
    ({}, '{}'),
    ({'a': 'd'}, '{"a": "d"}'),
    (2, '2'),
    (None, 'null'),
    (['a'], '["a"]'),
])
def test_header(v1, v2):
    serializer = JsonSerializer()
    assert v2 == serializer.serialize_header(v1)
    assert v1 == serializer.deserialize_header(v2)


@pytest.mark.gen_test
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
    with pytest.raises(TypeError):
        serializer.serialize_header({"sss"})

    with pytest.raises(ValueError):
        serializer.deserialize_header('{sss')

    with pytest.raises(TypeError):
        serializer.serialize_body({"sss"})

    with pytest.raises(ValueError):
        serializer.deserialize_body('{sss')