from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import transport

__all__ = ['Response']


class Response(object):
    def __init__(self, headers, body, transport):
        self.headers = headers
        self.body = body
        self.transport = transport


class ResponseTransportHeaders(transport.TransportHeaders):
    """Response-specific Transport Headers"""
    pass
