from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from collections import namedtuple

from tornado import gen

from .formats import DEFAULT_FORMATS
from .glossary import DEFAULT_TIMEOUT
from .tornado import TChannel as NodeInspiredTChannel
from .tornado.stream import InMemStream

__all__ = ['TChannel', 'Response']


class TChannel(NodeInspiredTChannel):

    def __init__(self, name, hostport=None, process_name=None,
                 known_peers=None, formatters=None, trace=False):

        super(TChannel, self).__init__(
            name, hostport, process_name, known_peers, trace
        )

        # if no formatters, use default
        if not formatters:
            formatters = DEFAULT_FORMATS

        # set formatters
        for f in formatters:
            f = f(self)
            setattr(self, f.name, f)

    @gen.coroutine
    def call(self, format, service, endpoint, body,
             headers=None, timeout=None):

        if headers is None:
            headers = ""  # should this be string???

        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        operation = self.request(
           hostport=service,
           arg_scheme=format
        )

        response = yield operation.send(
            InMemStream(endpoint),
            InMemStream(headers),
            InMemStream(body),
        )

        header = yield response.get_header()
        body = yield response.get_body()

        result = Response(header, body)

        raise gen.Return(result)


Response = namedtuple('Response', 'header, body')
