from __future__ import (
    absolute_import, division, print_function, unicode_literals
)


class BaseFormat(object):

    def __init__(self, tchannel):
        self.tchannel = tchannel
