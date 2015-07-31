from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import inspect

import pytest

from tchannel import from_thrift_module
from tchannel.thrift.generated import ThriftRequestMaker, ThriftRequest
from tests.data.generated.ThriftTest import ThriftTest


@pytest.mark.call
@pytest.mark.generated
def test_from_thrift_class_should_return_request_maker():

    maker = from_thrift_module('thrift_test', ThriftTest)

    assert isinstance(maker, ThriftRequestMaker)


@pytest.mark.call
@pytest.mark.generated
def test_maker_should_have_thrift_iface_methods():

    # TODO rename ThriftTest to less confusing module name, all lowercase
    maker = from_thrift_module('thrift_test', ThriftTest)

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
@pytest.mark.generated
def test_request_maker_should_return_request():

    maker = from_thrift_module('thrift_test', ThriftTest)

    request = maker.testString('hi')

    assert isinstance(request, ThriftRequest)
    assert request.service == 'thrift_test'
    assert request.endpoint == 'thrift_test::testString'
    assert request.args_type == ThriftTest.testString_args
    assert request.result_type == ThriftTest.testString_result
