from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import schemes

CALLER_NAME = "cn"
CLAIM_AT_START = "cas"
CLAIM_AT_FINISH = "caf"
FAILURE_DOMAIN = "fd"
RETRY_FLAGS = "re"
SCHEME = "as"
SHARD_KEY = "sk"
SPECULATIVE_EXE = "se"


def to_kwargs(data):

    args = {}
    args['caller_name'] = data.get(CALLER_NAME)
    args['claim_at_start'] = data.get(CLAIM_AT_START)
    args['claim_at_finish'] = data.get(CLAIM_AT_FINISH)
    args['failure_domain'] = data.get(FAILURE_DOMAIN)
    args['retry_flags'] = data.get(RETRY_FLAGS)
    args['scheme'] = data.get(SCHEME)
    args['shard_key'] = data.get(SHARD_KEY)
    args['speculative_exe'] = data.get(SPECULATIVE_EXE)

    return args


class TransportHeaders(object):
    """Transport Headers common between Request & Response"""

    def __init__(self, scheme=None, failure_domain=None, **kwargs):

        if scheme is None:
            scheme = schemes.DEFAULT

        self.scheme = scheme
        self.failure_domain = failure_domain
