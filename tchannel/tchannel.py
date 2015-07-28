from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from .format import Formatter
from .formats import DEFAULT_FORMATS
from .glossary import DEFAULT_TIMEOUT
from .tornado import TChannel as NodeInspiredTChannel

__all__ = ['TChannel']


class TChannel(NodeInspiredTChannel):

    def __init__(self, formatters=None):

        # if no formatters, use default
        if not formatters:
            formatters = DEFAULT_FORMATS

        # set formatters
        for f in formatters:
            # if not abc, blow up
            if not issubclass(f, Formatter):
                raise Exception("not valid formatter")

            # init and set on self
            f = f(self)
            setattr(self, f.name, f)

    @gen.coroutine
    def call(self, argscheme, service, endpoint, body,
             headers=None, timeout=None):

        if headers is None:
            headers = {}

        if timeout is None:
            timeout = DEFAULT_TIMEOUT
