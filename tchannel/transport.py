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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

CALLER_NAME = "cn"
CLAIM_AT_START = "cas"
CLAIM_AT_FINISH = "caf"
FAILURE_DOMAIN = "fd"
RETRY_FLAGS = "re"
ROUTING_DELEGATE = "rd"
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
    args['routing_delegate'] = data.get(ROUTING_DELEGATE)
    args['scheme'] = data.get(SCHEME)
    args['shard_key'] = data.get(SHARD_KEY)
    args['speculative_exe'] = data.get(SPECULATIVE_EXE)

    return args
