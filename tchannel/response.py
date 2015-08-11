from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import transport
from .tornado.response import StatusCode

__all__ = ['Response']


class Response(object):

    __slots__ = [
        'headers',
        'body',
        'transport',
        'code'
    ]
    # TODO implement __repr__

    def __init__(
        self,
        headers,
        body,
        transport,
        code=None,
    ):
        self.headers = headers
        self.body = body
        self.transport = transport
        self.code = code or StatusCode.ok

    @property
    def ok(self):
        return self.code == StatusCode.ok


class ResponseTransportHeaders(transport.TransportHeaders):

    # TODO add __slots__
    # TODO implement __repr__

    """Response-specific Transport Headers"""
    pass
