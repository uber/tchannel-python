from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import JSON
from .base import BaseFormat


class JsonFormat(BaseFormat):

    name = JSON

    def call(self):
        pass

    def stream(self):
        pass
