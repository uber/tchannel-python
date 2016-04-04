# Copyright (c) 2016 Uber Technologies, Inc.
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

"""
VCR
===

``tchannel.testing.vcr`` provides VCR-like functionality for TChannel. Its
API is heavily inspired by the `vcrpy <https://github.com/kevin1024/vcrpy/>`_
library.

This allows recording TChannel requests and their responses into YAML files
during integration tests and replaying those recorded responses when the tests
are run next time.

The simplest way to use this is with the :py:func:`use_cassette` function.

.. autofunction:: use_cassette

Configuration
-------------

.. py:data:: tchannel.testing.vcr.DEFAULT_MATCHERS

    A tuple containing the default list of matchers used by
    :py:func:`tchannel.testing.vcr.use_cassette`.

Record Modes
~~~~~~~~~~~~

.. autoclass:: RecordMode

"""

from __future__ import absolute_import

from .config import use_cassette
from .record_modes import RecordMode
from .cassette import DEFAULT_MATCHERS


__all__ = ['use_cassette', 'RecordMode', 'DEFAULT_MATCHERS']
