from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from collections import namedtuple

from tornado import gen

from . import formats, scheme
from .glossary import DEFAULT_TIMEOUT
from .tornado import TChannel as DeprecatedTChannel
from .tornado.broker import ArgSchemeBroker

__all__ = ['TChannel', 'Response']


class TChannel(object):

    def __init__(self, name, hostport=None, process_name=None,
                 known_peers=None, formatters=None, trace=False):

        # until we move everything here,
        # lets compose the old tchannel
        self._dep_tchannel = DeprecatedTChannel(
            name, hostport, process_name, known_peers, trace
        )

        # if no formatters, use defaults
        if not formatters:
            formatters = formats.DEFAULT_FORMATS

        # set formatters
        for f in formatters:
            f = f(self)
            setattr(self, f.name, f)

    @gen.coroutine  # TODO dont use coroutine
    def call(self, format, service, arg1, arg2, arg3, timeout=None):

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

        # execute response, note that formats.RAW
        # goes to the else clause; this allows custom
        # formats to continue to work. TODO this function
        # should have no specialization per-format.
        if format == formats.JSON:
            response = yield ArgSchemeBroker(scheme.JsonArgScheme()).send(
                client=operation,
                endpoint=arg1,
                header=arg2,
                body=arg3,
            )
        else:
            response = yield operation.send(
                arg1=arg1,
                arg2=arg2,
                arg3=arg3,
            )

        # unwrap response
        header = yield response.get_header()
        body = yield response.get_body()
        result = Response(header, body)

        raise gen.Return(result)


Response = namedtuple('Response', 'header, body')
