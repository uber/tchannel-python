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

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

#: Retry the request on failures to connect to a remote host. This is the
#: default retry behavior.
CONNECTION_ERROR = 'c'

#: Never retry the request.
NEVER = 'n'

#: Retry the request on timeouts waiting for a response.
TIMEOUT = 't'

#: Retry the request on failures to connect and timeouts after connecting.
CONNECTION_ERROR_AND_TIMEOUT = 'ct'

DEFAULT = CONNECTION_ERROR

#: The default number of times to retry a request. This is in addition to the
#: original request.
DEFAULT_RETRY_LIMIT = 4
