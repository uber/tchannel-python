from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import RAW


class RawFormat(object):
    """Semantic params and serialization for raw."""

    NAME = RAW

    def __init__(self, tchannel):
        self.tchannel = tchannel

    def __call__(self, service, endpoint, body=None,
                 header=None, timeout=None):

        return self.tchannel.call(
            format=self.NAME,
            service=service,
            arg1=endpoint,
            arg2=header,
            arg3=body,
            timeout=timeout,
        )

    def stream(self):
        pass
