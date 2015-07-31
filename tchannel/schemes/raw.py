from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import RAW


class RawArgScheme(object):
    """Semantic params and serialization for raw."""

    NAME = RAW

    def __init__(self, tchannel):
        self._tchannel = tchannel

    def __call__(self, service, endpoint, body=None,
                 header=None, timeout=None):

        return self._tchannel.call(
            scheme=self.NAME,
            service=service,
            arg1=endpoint,
            arg2=header,
            arg3=body,
            timeout=timeout,
        )

    def stream(self):
        pass

    def register(self):
        pass
