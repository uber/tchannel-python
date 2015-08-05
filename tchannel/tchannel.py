from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from . import schemes, transport, retry
from .glossary import DEFAULT_TIMEOUT
from .response import Response, ResponseTransportHeaders
from .tornado import TChannel as DeprecatedTChannel

__all__ = ['TChannel']


class TChannel(object):

    def __init__(self, name, listen_on=None, process_name=None,
                 known_peers=None, trace=False):

        # until we move everything here,
        # lets compose the old tchannel
        self._dep_tchannel = DeprecatedTChannel(
            name=name,
            hostport=listen_on,
            process_name=process_name,
            known_peers=known_peers,
            trace=trace
        )

        self.name = name

        # set arg schemes
        self.raw = schemes.RawArgScheme(self)
        self.json = schemes.JsonArgScheme(self)
        self.thrift = schemes.ThriftArgScheme(self)

    @gen.coroutine
    def call(self, scheme, service, arg1, arg2=None, arg3=None,
             timeout=None, retry_on=None, retry_limit=None, hostport=None):

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
        if retry_on is None:
            retry_on = retry.DEFAULT
        if retry_limit is None:
            retry_limit = retry.DEFAULT_RETRY_LIMIT

        # calls tchannel.tornado.peer.PeerClientOperation.__init__
        operation = self._dep_tchannel.request(
            service=service,
            hostport=hostport,
            arg_scheme=scheme,
            retry=retry_on,
        )

        # fire operation
        transport_headers = {
            transport.SCHEME: scheme,
            transport.CALLER_NAME: self.name,
        }
        response = yield operation.send(
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            headers=transport_headers,
            attempt_times=retry_limit,
            ttl=timeout,
        )

        # unwrap response
        header = yield response.get_header()
        body = yield response.get_body()
        t = transport.to_kwargs(response.headers)
        t = ResponseTransportHeaders(**t)

        result = Response(header, body, t)

        raise gen.Return(result)
