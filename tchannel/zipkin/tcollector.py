from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tchannel import thrift

tcollector = thrift.load('./tcollector.thrift', 'tcollector')
