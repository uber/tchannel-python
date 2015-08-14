from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import transport

__all__ = ['Response']


class Response(object):

    # TODO add __slots__
    # TODO implement __repr__

    def __init__(self, body=None, headers=None, transport=None):
        self.body = body
        self.headers = headers or {}
        self.transport = transport


class ResponseTransportHeaders(transport.TransportHeaders):

    # TODO add __slots__
    # TODO implement __repr__

    """Response-specific Transport Headers"""
    pass
