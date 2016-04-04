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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from threading import local

from . import TChannel as AsyncTChannel
from .errors import SingletonNotPreparedError


class TChannel(object):
    """Maintain a single TChannel instance per-thread."""

    tchannel_cls = AsyncTChannel

    local = local()
    local.tchannel = None

    prepared = False
    args = None
    kwargs = None

    @classmethod
    def prepare(cls, *args, **kwargs):
        """Set arguments to be used when instantiating a TChannel instance.

        Arguments are the same as :py:meth:`tchannel.TChannel.__init__`.
        """
        cls.args = args
        cls.kwargs = kwargs
        cls.prepared = True

    @classmethod
    def reset(cls, *args, **kwargs):
        """Undo call to prepare, useful for testing."""
        cls.local.tchannel = None
        cls.args = None
        cls.kwargs = None
        cls.prepared = False

    @classmethod
    def get_instance(cls):
        """Get a configured, thread-safe, singleton TChannel instance.

        :returns tchannel.TChannel:
        """
        if not cls.prepared:
            raise SingletonNotPreparedError(
                "prepare must be called before get_instance"
            )

        if hasattr(cls.local, 'tchannel') and cls.local.tchannel is not None:
            return cls.local.tchannel

        cls.local.tchannel = cls.tchannel_cls(*cls.args, **cls.kwargs)

        return cls.local.tchannel
