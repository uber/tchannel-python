from __future__ import (
    absolute_import, division, print_function, unicode_literals
)


class Request(object):

    def __init__(self, body=None, headers=None, transport=None):
        self.body = body
        self.headers = headers
        self.transport = transport
