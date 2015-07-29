from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import RAW
from .base import BaseFormat


class RawFormat(BaseFormat):
    """Add semantic params and serialization for raw."""

    name = RAW

    def call(self, service, endpoint, body=None,
             headers=None, timeout=None):

        return self.tchannel.call(
            format=self.name,
            service=service,
            arg1=endpoint,
            arg2=headers,
            arg3=body,
            timeout=timeout,
        )

    def stream(self):
        pass
