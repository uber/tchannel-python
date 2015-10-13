from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from threading import local

from tchannel.singleton import TChannel as TChannelSingleton
from .client import TChannel as SyncTChannel


class TChannel(TChannelSingleton):

    tchannel_cls = SyncTChannel

    local = local()
    local.tchannel = None

    prepared = False
    args = None
    kwargs = None

    @classmethod
    def get_instance(cls):
        """Get a configured, thread-safe, singleton TChannel instance.

        :returns: tchannel.sync.TChannel
        """
        return super(TChannel, cls).get_instance()
