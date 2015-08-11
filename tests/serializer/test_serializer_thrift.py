import pytest
from tchannel.serializer.thrift import ThriftSerializer
from tchannel.testing.data.generated.ThriftTest.ThriftTest import \
    testStruct_result
from tchannel.testing.data.generated.ThriftTest.ttypes import Xtruct


@pytest.mark.parametrize('v1', [
    ({}),
    ({'a': 'd'}),
])
def test_header(v1):
    serializer = ThriftSerializer(None)
    assert v1 == serializer.deserialize_header(
        serializer.serialize_header(v1)
    )


def test_body():
    result = testStruct_result(Xtruct("s", 0, 1, 2))
    serializer = ThriftSerializer(testStruct_result)
    assert result == serializer.deserialize_body(
        serializer.serialize_body(result)
    )
