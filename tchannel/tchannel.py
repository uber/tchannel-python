from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from .glossary import DEFAULT_TIMEOUT
from .tornado import TChannel as NodeInspiredTChannel

__all__ = ['TChannel']


class TChannel(NodeInspiredTChannel):

    @gen.coroutine
    def call(self, argscheme, service, endpoint, body, headers=None, timeout=None):

        if headers is None:
            headers = {}

        if timeout is None:
            timeout = DEFAULT_TIMEOUT

    @gen.coroutine
    def call_raw(self, service, endpoint, body, headers=None, timeout=None):

        response = yield self.call('raw', service, endpoint, body, timeout)

        raise gen.Return(response)

    @gen.coroutine
    def call_json(self):
        pass

    @gen.coroutine
    def call_http(self):
        pass

    @gen.coroutine
    def call_thrift(self):
        pass

