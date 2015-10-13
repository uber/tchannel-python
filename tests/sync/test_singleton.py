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

from tchannel.sync.singleton import TChannel
from tchannel.sync import TChannel as SyncTChannel
from tchannel.singleton import TChannel as AsyncSingleton
from tchannel.errors import SingletonNotPreparedError


def test_stored_seperately_from_async_singleton():

    TChannel.reset()
    AsyncSingleton.reset()

    AsyncSingleton.prepare('async-app')

    with pytest.raises(SingletonNotPreparedError):
        TChannel.get_instance()

    TChannel.prepare('sync-app')

    instance = TChannel.get_instance()

    assert isinstance(instance,  SyncTChannel)
    assert AsyncSingleton.get_instance() is not instance
