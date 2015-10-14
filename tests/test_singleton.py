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
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel as AsyncTChannel
from tchannel.singleton import TChannel
from tchannel.errors import SingletonNotPreparedError


def test_get_instance_is_singleton():

    TChannel.reset()
    TChannel.prepare('my-app')

    assert TChannel.get_instance() is TChannel.get_instance()


def test_must_call_prepare_before_get_instance():

    TChannel.reset()

    with pytest.raises(SingletonNotPreparedError):
        TChannel.get_instance()


def test_get_instance_returns_configured_tchannel():

    TChannel.reset()
    TChannel.prepare('my-app')

    tchannel = TChannel.get_instance()

    assert isinstance(tchannel, AsyncTChannel)
    assert tchannel.name == 'my-app'
