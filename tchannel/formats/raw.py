from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import RAW
from .base import BaseFormat


class RawFormat(BaseFormat):

    name = RAW

    def call(self, service, endpoint, body,
             headers=None, timeout=None):

        return self.tchannel.call(
            format=self.name,
            service=service,
            endpoint=endpoint,
            body=body,
            headers=headers,
            timeout=timeout,
        )

    def stream(self):
        pass
