from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from .tornado.tchannel import TChannel as NodeInspiredTChannel


class TChannel(NodeInspiredTChannel):

    def call(self):
        pass
