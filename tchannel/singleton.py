from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from threading import local

from tchannel import TChannel as AsyncTChannel


class TChannel(object):

    prepared = False
    args = None
    kwargs = None

    tchannel_cls = AsyncTChannel

    local = local()
    local.tchannel = None

    @classmethod
    def prepare(cls, *args, **kwargs):
        cls.args = args
        cls.kwargs = kwargs
        cls.prepared = True

    @classmethod
    def get_instance(cls):

        if not cls.prepared:
            # TODO use better exception
            raise Exception("prepare must be called before get_instance")

        if hasattr(cls.local, 'tchannel') and cls.local.tchannel is not None:
            return cls.local.tchannel

        cls.local.tchannel = cls.tchannel_cls(*cls.args, **cls.kwargs)

        return cls.local.tchannel
