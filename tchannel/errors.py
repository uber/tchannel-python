# Copyright (c) 2016 Uber Technologies, Inc.
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

#: The request timed out.
TIMEOUT = 0x01

#: The request was canceled.
CANCELED = 0x02

#: The server was busy.
BUSY = 0x03

# The server declined the request.
DECLINED = 0x04

# The server's handler raised an unexpected exception.
UNEXPECTED_ERROR = 0x05

#: The request was bad.
BAD_REQUEST = 0x06

#: There was a network error when sending the request.
NETWORK_ERROR = 0x07

#: The server handling the request is unhealthy.
UNHEALTHY = 0x08

#: There was a fatal protocol-level error.
FATAL = 0xFF


class TChannelError(Exception):
    """A TChannel-generated exception.

    :ivar code:
        The error code for this error. See the `Specification`_ for a
        description of these codes.
    :vartype code:

    .. _`Specification`:
            http://tchannel.readthedocs.org/en/latest/protocol/#code1_1
    """

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
        """Construct a ``TChannelError`` instance from an error code.

        This will return the appropriate class type for the given code.
        """
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


class RetryableError(TChannelError):
    """An error where the original request is always safe to retry.

    It is always safe to retry a request with this category of errors. The
    original request was never handled.
    """


class MaybeRetryableError(TChannelError):
    """An error where the original request may be safe to retry.

    The original request may have reached the intended service. Hence, the
    request should only be retried if it is known to be `idempotent`_.

    .. _`idempotent`:
        https://en.wikipedia.org/wiki/Idempotence#Computer_science_meaning
    """


class NotRetryableError(TChannelError):
    """An error where the original request should not be re-sent.

    Something was fundamentally wrong with the request and it should not be
    retried.
    """


class TimeoutError(MaybeRetryableError):
    code = TIMEOUT


class CanceledError(NotRetryableError):
    code = CANCELED


class BusyError(RetryableError):
    code = BUSY


class DeclinedError(RetryableError):
    code = DECLINED


class UnexpectedError(MaybeRetryableError):
    code = UNEXPECTED_ERROR


class BadRequestError(NotRetryableError):
    code = BAD_REQUEST


class NetworkError(MaybeRetryableError):
    code = NETWORK_ERROR


class UnhealthyError(NotRetryableError):
    code = UNHEALTHY


class FatalProtocolError(NotRetryableError):
    code = FATAL


class ReadError(FatalProtocolError):
    """Raised when there is an error while reading input."""
    pass


class InvalidChecksumError(FatalProtocolError):
    """Represent invalid checksum type in the message"""
    pass


class NoAvailablePeerError(RetryableError):
    """Represents a failure to find any peers for a request."""
    pass


class AlreadyListeningError(FatalProtocolError):
    """Raised when attempting to listen multiple times."""
    pass


class OneWayNotSupportedError(BadRequestError):
    """Raised when a one-way Thrift procedure is called."""
    pass


class ValueExpectedError(BadRequestError):
    """Raised when a non-void Thrift response contains no value."""
    pass


class SingletonNotPreparedError(TChannelError):
    """Raised when calling get_instance before calling prepare."""
    pass
