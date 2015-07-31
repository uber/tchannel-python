from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

NEVER = 'n'
CONNECTION_ERROR = 'c'
TIMEOUT = 't'
CONNECTION_ERROR_AND_TIMEOUT = 'ct'
DEFAULT = CONNECTION_ERROR

DEFAULT_RETRY_LIMIT = 3
DEFAULT_RETRY_DELAY = 0.3  # 300 ms
