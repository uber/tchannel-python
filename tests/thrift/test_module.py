from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import inspect

import pytest

from tchannel import thrift_request_builder
from tchannel.testing.data.generated.ThriftTest import ThriftTest
from tchannel.thrift.module import ThriftRequest
from tchannel.thrift.module import ThriftRequestMaker


@pytest.mark.call
def test_from_thrift_class_should_return_request_maker():

    maker = thrift_request_builder('thrift_test', ThriftTest)

    assert isinstance(maker, ThriftRequestMaker)


@pytest.mark.call
def test_maker_should_have_thrift_iface_methods():

    maker = thrift_request_builder('thrift_test', ThriftTest)

    # extract list of maker methods
    maker_methods = [
        m[0] for m in
        inspect.getmembers(maker, predicate=inspect.ismethod)
    ]

    # extract list of iface methods
    iface_methods = [
        m[0] for m in
        inspect.getmembers(ThriftTest.Iface, predicate=inspect.ismethod)
    ]

    # verify all of iface_methods exist in maker_methods
    assert set(iface_methods) < set(maker_methods)


@pytest.mark.call
def test_request_maker_should_return_request():

    maker = thrift_request_builder('thrift_test', ThriftTest)

    request = maker.testString('hi')

    assert isinstance(request, ThriftRequest)
    assert request.service == 'thrift_test'
    assert request.endpoint == 'ThriftTest::testString'
    assert request.result_type == ThriftTest.testString_result
    assert request.call_args == ThriftTest.testString_args(thing='hi')
