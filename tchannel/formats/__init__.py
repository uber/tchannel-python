from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

RAW = 'raw'
JSON = 'json'
THRIFT = 'thrift'

from .raw import RawFormat  # noqa
from .json import JsonFormat  # noqa
from .thrift import ThriftFormat  # noqa

DEFAULT_FORMATS = (
    RawFormat,
    JsonFormat,
    ThriftFormat
)
