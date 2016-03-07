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

from __future__ import (
    absolute_import, unicode_literals, print_function, division
)

import pytest
from tornado import gen

from tchannel.tornado.tombstone import Cemetery


@pytest.mark.gen_test
def test_add_and_forget():
    cem = Cemetery(ttl_offset_secs=0.01)
    cem.add(1, 0.01)
    cem.add(2, 0.05)

    assert 1 in cem
    assert 2 in cem

    yield gen.sleep(0.020)

    assert 1 not in cem
    assert 2 in cem


@pytest.mark.gen_test
def test_add_and_explicit_forget():
    cem = Cemetery(ttl_offset_secs=0.01)
    cem.add(1, 0.05)

    yield gen.sleep(0.04)

    assert 1 in cem
    cem.forget(1)
    assert 1 not in cem


@pytest.mark.gen_test
def test_max_ttl():
    cem = Cemetery(max_ttl_secs=0.05)
    cem.add(1, 0.2)

    assert 1 in cem
    yield gen.sleep(0.05)
    assert 1 not in cem


@pytest.mark.gen_test
def test_clear():
    cem = Cemetery()
    cem.add(1, 0.1)
    cem.add(2, 0.2)

    assert 1 in cem
    assert 2 in cem

    cem.clear()

    assert 1 not in cem
    assert 2 not in cem
