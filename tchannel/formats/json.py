from __future__ import (
    absolute_import, division, print_function, unicode_literals
)


from tchannel.format import Formatter


class JsonFormat(Formatter):

    name = 'json'

    def call(self):
        pass

    def stream(self):
        pass
