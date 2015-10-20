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
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import inspect

import pytest

from tchannel import thrift_request_builder
from tchannel.thrift.module import ThriftRequest
from tchannel.thrift.module import ThriftRequestMaker
from tests.data.generated.ThriftTest import ThriftTest


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
