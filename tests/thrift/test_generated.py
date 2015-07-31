from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import from_thrift_module
from tchannel.thrift.generated import ThriftRequest
from tests.data.generated.ThriftTest import ThriftTest


@pytest.mark.call
@pytest.mark.generated
def test_from_thrift_class_should_return_request_maker():

    maker = from_thrift_module("thrift_test", ThriftTest)

    import ipdb
    ipdb.set_trace()

    request = maker.testString("hi")

    assert isinstance(request, ThriftRequest)
    assert request.endpoint == 'thrift_test::testString'
    assert request.body == 'hi'

    assert maker
