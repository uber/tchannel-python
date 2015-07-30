from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from . import formats, transport
from .glossary import DEFAULT_TIMEOUT
from .response import Response, ResponseTransportHeaders
from .tornado import TChannel as DeprecatedTChannel

__all__ = ['TChannel']


class TChannel(object):

    def __init__(self, name, hostport=None, process_name=None,
                 known_peers=None, trace=False):

        # until we move everything here,
        # lets compose the old tchannel
        self._dep_tchannel = DeprecatedTChannel(
            name, hostport, process_name, known_peers, trace
        )

        # set formatters
        self.raw = formats.RawFormat(self)
        self.json = formats.JsonFormat(self)
        self.thrift = formats.ThriftFormat(self)

    @gen.coroutine
    def call(self, format, service, arg1, arg2=None, arg3=None, timeout=None):

        # TODO - dont use asserts for public API
        assert format, "format is required"
        assert service, "service is required"
        assert arg1, "arg1 is required"

        # default args
        if arg2 is None:
            arg2 = ""
        if arg3 is None:
            arg3 = ""
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        # get operation
        # TODO lets treat hostport and service as the same param
        operation = self._dep_tchannel.request(
           hostport=service,
           arg_scheme=format
        )

        # fire operation
        response = yield operation.send(
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
        )

        # unwrap response
        header = yield response.get_header()
        body = yield response.get_body()
        t = transport.to_kwargs(response.headers)
        t = ResponseTransportHeaders(**t)

        result = Response(header, body, t)

        raise gen.Return(result)
