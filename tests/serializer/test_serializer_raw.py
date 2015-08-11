from __future__ import absolute_import

from tchannel.serializer.raw import RawSerializer


def test_header():
    serializer = RawSerializer()
    obj = object()
    assert obj == serializer.serialize_header(obj)
    assert obj == serializer.deserialize_header(obj)


def test_body():
    serializer = RawSerializer()
    obj = object()
    assert obj == serializer.serialize_body(obj)
    assert obj == serializer.deserialize_body(obj)
