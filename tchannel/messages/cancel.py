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

from __future__ import absolute_import

from . import common
from .. import rw
from ..glossary import DEFAULT_TIMEOUT
from .base import BaseMessage


class CancelMessage(BaseMessage):
    __slots__ = BaseMessage.__slots__ + (
        'ttl',
        'tracing',
        'why',
    )

    def __init__(self, ttl=DEFAULT_TIMEOUT, tracing=None, why=None, id=0):
        super(CancelMessage, self).__init__(id)
        self.ttl = ttl
        self.tracing = tracing or common.Tracing(0, 0, 0, 0)
        self.why = why or ''


cancel_rw = rw.instance(
    CancelMessage,
    ('ttl', rw.number(4)),                          # ttl:4
    ('tracing', common.tracing_rw),                 # tracing:24
    ('why', rw.len_prefixed_string(rw.number(2))),  # why:2
)
