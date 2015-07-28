from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import THRIFT
from .base import BaseFormat


class ThriftFormat(BaseFormat):

    name = THRIFT

    def call(self):
        pass

    def stream(self):
        pass
