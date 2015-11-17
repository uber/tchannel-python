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

import platform

from . import __version__

# Largest message ID supported by the system.
# Message ID 0xffffffff is reserved
MAX_MESSAGE_ID = 0xfffffffe

# CallRequestMessage uses it as the default TTL value for the message.
DEFAULT_TIMEOUT = 30  # seconds

TCHANNEL_LANGUAGE = 'python'

# python environment, eg 'CPython-2.7.10'
TCHANNEL_LANGUAGE_VERSION = (
    platform.python_implementation() + '-' + platform.python_version()
)

# version format x.y.z
TCHANNEL_VERSION = __version__

# Max size of arg1.
MAX_SIZE_OF_ARG1 = 16 * 1024
