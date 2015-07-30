from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

RAW = 'raw'
JSON = 'json'
THRIFT = 'thrift'
DEFAULT = RAW

DEFAULT_NAMES = (
    RAW,
    JSON,
    THRIFT
)

from .raw import RawArgScheme  # noqa
from .json import JsonArgScheme  # noqa
from .thrift import ThriftArgScheme  # noqa

DEFAULT_SCHEMES = (
    RawArgScheme,
    JsonArgScheme,
    ThriftArgScheme
)
