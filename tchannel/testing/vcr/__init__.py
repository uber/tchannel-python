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

"""This module provides VCR-like functionality for TChannel.

.. code-block:: python

    from tchannel.testing import vcr

    @vcr.use_cassette('tests/data/foo.yaml')
    def test_foo():
        channel = TChannel('test-client')
        service_client = MyServiceClient(channel)

        yield service_client.myMethod()

It is heavily inspired by the `vcrpy <https://github.com/kevin1024/vcrpy/>`_
library.
"""
from __future__ import absolute_import

from .patch import Patcher
from .cassette import Cassette


def use_cassette(path):
    # TODO create some sort of configurable VCR object which implements
    # use_cassette. Top-level use_cassette can just use a default instance.
    return Patcher(Cassette(path))


__all__ = ['use_cassette']
