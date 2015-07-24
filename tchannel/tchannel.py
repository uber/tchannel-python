from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from .tornado import TChannel as NodeInspiredTChannel

__all__ = ['TChannel']


class TChannel(NodeInspiredTChannel):

    def call(self, argscheme):
        pass

    def call_raw(self):
        pass

    def call_json(self):
        pass

    def call_http(self):
        pass

    def call_thrift(self):
        pass

