from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import from_thrift_class


@pytest.mark.call
def test_from_thrift_class_should_return_request_set():
    request_set = from_thrift_class('some_generated_thrift_class')

    assert request_set
