from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import RAW


class RawArgScheme(object):
    """Semantic params and serialization for raw."""

    NAME = RAW

    def __init__(self, tchannel):
        self._tchannel = tchannel

    def __call__(self, service, endpoint, body=None, headers=None,
                 timeout=None, retry_on=None, retry_limit=None, hostport=None):

        return self._tchannel.call(
            scheme=self.NAME,
            service=service,
            arg1=endpoint,
            arg2=headers,
            arg3=body,
            timeout=timeout,
            retry_on=retry_on,
            retry_limit=retry_limit,
            hostport=hostport,
        )
