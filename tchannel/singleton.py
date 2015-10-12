from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from threading import local

from . import TChannel as AsyncTChannel
from .errors import TChannelError


class TChannel(object):
    """Maintain a single TChannel instance per-thread."""

    prepared = False
    args = None
    kwargs = None

    tchannel_cls = AsyncTChannel

    local = local()
    local.tchannel = None

    @classmethod
    def prepare(cls, *args, **kwargs):
        """Set arguments to be used when instantiating a TChannel instance.

        TODO somehow inherit TChannel.init docs
        """
        cls.args = args
        cls.kwargs = kwargs
        cls.prepared = True

    @classmethod
    def get_instance(cls):
        """Get a configured, thread-safe, singleton TChannel instance.

        :returns tchannel.TChannel:
        """
        if not cls.prepared:
            raise SingletonNotPreparedError(
                "prepare must be called before get_instance"
            )

        if hasattr(cls.local, 'tchannel') and cls.local.tchannel is not None:
            return cls.local.tchannel

        cls.local.tchannel = cls.tchannel_cls(*cls.args, **cls.kwargs)

        return cls.local.tchannel


class SingletonNotPreparedError(TChannelError):
    """Raised when calling get_instance before calling prepare."""
    pass
