from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from .glossary import DEFAULT_TIMEOUT
from .tornado import TChannel as NodeInspiredTChannel

__all__ = ['TChannel']


class TChannel(NodeInspiredTChannel):

    @gen.coroutine
    def call(self, argscheme, service, endpoint, body, headers={}, timeout=DEFAULT_TIMEOUT):
        pass

    @gen.coroutine
    def call_raw(self):
        pass

    @gen.coroutine
    def call_json(self):
        pass

    @gen.coroutine
    def call_http(self):
        pass

    @gen.coroutine
    def call_thrift(self):
        pass

