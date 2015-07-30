from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import THRIFT


class ThriftArgScheme(object):

    NAME = THRIFT

    def __init__(self, tchannel):
        self.tchannel = tchannel

    def __call__(self):
        pass

    def stream(self):
        pass

    def register(self):
        pass
