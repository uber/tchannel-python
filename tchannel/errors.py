# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import


TIMEOUT = 0x01
CANCELED = 0x02
BUSY = 0x03
DECLINED = 0x04
UNEXPECTED_ERROR = 0x05
BAD_REQUEST = 0x06
NETWORK_ERROR = 0x07
UNHEALTHY = 0x08
FATAL = 0xFF


class TChannelError(Exception):
    """Represent a TChannel-generated exception."""

    __slots__ = (
        'code',
        'description',
        'id',
        'tracing',
    )

    code = None

    def __init__(
        self,
        description=None,
        id=None,
        tracing=None,
    ):
        super(TChannelError, self).__init__(description)
        self.tracing = tracing
        self.id = id
        self.description = description

    @classmethod
    def from_code(cls, code, **kw):
        return {
            TIMEOUT: TimeoutError,
            CANCELED: CanceledError,
            BUSY: BusyError,
            DECLINED: DeclinedError,
            UNEXPECTED_ERROR: UnexpectedError,
            BAD_REQUEST: BadRequestError,
            NETWORK_ERROR: NetworkError,
            UNHEALTHY: UnhealthyError,
            FATAL: FatalProtocolError,
        }[code](**kw)


class AlwaysRetryableError(TChannelError):
    pass


class PossiblyRetryableError(TChannelError):
    pass


class UnretryableError(TChannelError):
    pass


class TimeoutError(PossiblyRetryableError):
    code = TIMEOUT


class CanceledError(UnretryableError):
    code = CANCELED


class BusyError(AlwaysRetryableError):
    code = BUSY


class DeclinedError(AlwaysRetryableError):
    code = DECLINED


class UnexpectedError(PossiblyRetryableError):
    code = UNEXPECTED_ERROR


class BadRequestError(UnretryableError):
    code = BAD_REQUEST


class NetworkError(PossiblyRetryableError):
    code = NETWORK_ERROR


class UnhealthyError(UnretryableError):
    code = UNHEALTHY


class FatalProtocolError(UnretryableError):
    code = FATAL


class ReadError(FatalProtocolError):
    """Raised when there is an error while reading input."""
    pass


class InvalidChecksumError(FatalProtocolError):
    """Represent invalid checksum type in the message"""
    pass


class NoAvailablePeerError(AlwaysRetryableError):
    """Represents a failure to find any peers for a request."""
    pass


class AlreadyListeningError(FatalProtocolError):
    """Represents exception from attempting to listen multiple times."""
    pass


class OneWayNotSupportedError(BadRequestError):
    """Raised when oneway Thrift procedure is called."""
    pass


class ValueExpectedError(BadRequestError):
    """Raised when a non-void Thrift response contains no value."""
    pass
