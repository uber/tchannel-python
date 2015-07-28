from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from .base import BaseFormat


class RawFormat(BaseFormat):

    name = 'raw'

    def call(self):
        pass

    def stream(self):
        pass
