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
    absolute_import, unicode_literals, division, print_function
)

from tornado import gen

import pytest

from tchannel._future import fail_to


def test_fail_to_no_failure():
    answer = gen.Future()

    @fail_to(answer)
    def f():
        return 42

    assert f() == 42
    assert answer.running()


@pytest.mark.gen_test
def test_fail_to_failure():
    answer = gen.Future()

    @fail_to(answer)
    def f():
        raise GreatSadness

    assert f() is None
    with pytest.raises(GreatSadness):
        yield answer


@pytest.mark.gen_test
@pytest.mark.gen_test
def test_fail_to_failure_in_coroutine():
    answer = gen.Future()

    @fail_to(answer)
    @gen.coroutine
    def f():
        raise GreatSadness

    with pytest.raises(GreatSadness):
        yield f()
    assert answer.running()


class GreatSadness(Exception):
    pass
