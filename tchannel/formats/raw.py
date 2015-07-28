from __future__ import (
    absolute_import, division, print_function, unicode_literals
)


from tchannel.format import Formatter


class RawFormat(Formatter):

    @property
    def name(self):
        return 'raw'

    def call(self):
        pass

    def stream(self):
        pass
