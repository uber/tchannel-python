from __future__ import absolute_import
import pytest

from tchannel.serializer.json import JsonSerializer


def test_header(v1, v2):
    serializer = JsonSerializer()
    obj = object()
    assert obj == serializer.serialize_header(obj)
    assert obj == serializer.deserialize_header(obj)


def test_body():
    serializer = JsonSerializer()
    obj = object()
    assert obj == serializer.serialize_body(obj)
    assert obj == serializer.deserialize_body(obj)