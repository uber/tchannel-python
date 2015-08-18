from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import schemes

__all__ = ['Request']


class Request(object):
    """TChannel Request"""

    # TODO move over other props from tchannel.tornado.request

    __slots__ = (
        'body',
        'headers',
        'transport'
    )

    def __init__(self, body=None, headers=None, transport=None):
        self.body = body
        self.headers = headers
        self.transport = transport


class TransportHeaders(object):
    """Request Transport Headers"""

    # TODO implement __repr__
    # TODO retry_flags should be woke up past a string

    __slots__ = (
        'caller_name',
        'claim_at_start',
        'claim_at_finish',
        'failure_domain',
        'retry_flags',
        'scheme',
        'speculative_exe',
    )

    def __init__(self,
                 caller_name=None,
                 claim_at_start=None,
                 claim_at_finish=None,
                 failure_domain=None,
                 retry_flags=None,
                 scheme=None,
                 speculative_exe=None,
                 **kwargs):

        if scheme is None:
            scheme = schemes.RAW

        self.caller_name = caller_name
        self.claim_at_start = claim_at_start
        self.claim_at_finish = claim_at_finish
        self.failure_domain = failure_domain
        self.retry_flags = retry_flags
        self.scheme = scheme
        self.speculative_exe = speculative_exe
