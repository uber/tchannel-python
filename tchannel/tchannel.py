from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from tornado import gen

from . import schemes, transport, retry
from .glossary import DEFAULT_TIMEOUT
from .response import Response, ResponseTransportHeaders
from .tornado import TChannel as DeprecatedTChannel
from .tornado.dispatch import RequestDispatcher as DeprecatedDispatcher

__all__ = ['TChannel']


class TChannel(object):
    """Make requests to TChannel services."""

    def __init__(self, name, hostport=None, process_name=None,
                 known_peers=None, trace=False):

        # until we move everything here,
        # lets compose the old tchannel
        self._dep_tchannel = DeprecatedTChannel(
            name=name,
            hostport=hostport,
            process_name=process_name,
            known_peers=known_peers,
            trace=trace,
            dispatcher=DeprecatedDispatcher(_handler_returns_response=True),
        )

        self.name = name

        # set arg schemes
        self.raw = schemes.RawArgScheme(self)
        self.json = schemes.JsonArgScheme(self)
        self.thrift = schemes.ThriftArgScheme(self)

    @gen.coroutine
    def call(self, scheme, service, arg1, arg2=None, arg3=None,
             timeout=None, retry_on=None, retry_limit=None, hostport=None):
        """Make low-level requests to TChannel services.

        This method uses TChannel's protocol terminology for param naming.

        For high level requests with automatic serialization and semantic
        param names, use ``raw``, ``json``, and ``thrift`` methods instead.

        :param string scheme:
            Name of the Arg Scheme to be sent as the Transport Header ``as``;
            eg. 'raw', 'json', 'thrift' are all valid values.
        :param string service:
            Name of the service that is being called. This is used
            internally to route requests through Hyperbahn, and for grouping
            of connection, and labelling stats. Note that when hostport is
            provided, requests are not routed through Hyperbahn.
        :param string arg1:
            Value for ``arg1`` as specified by the TChannel protocol - this
            varies by Arg Scheme, but is typically used for endpoint name.
        :param string arg2:
            Value for ``arg2`` as specified by the TChannel protocol - this
            varies by Arg Scheme, but is typically used for app-level headers.
        :param string arg3:
            Value for ``arg3`` as specified by the TChannel protocol - this
            varies by Arg Scheme, but is typically used for the request body.
        :param int timeout:
            How long to wait before raising a ``TimeoutError`` - this
            defaults to ``tchannel.glossary.DEFAULT_TIMEOUT``.
        :param string retry_on:
            What events to retry on - valid values can be found in
            ``tchannel.retry``.
        :param string retry_limit:
            How many times to retry before
        :param string hostport:
            A 'host:port' value to use when making a request directly to a
            TChannel service, bypassing Hyperbahn.
        """

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

        # TODO - allow filters/steps for serialization, tracing, etc...

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
        body = yield response.get_body()
        headers = yield response.get_header()
        t = transport.to_kwargs(response.headers)
        t = ResponseTransportHeaders(**t)

        result = Response(body, headers, t)

        raise gen.Return(result)

    def listen(self, port=None):
        return self._dep_tchannel.listen(port)

    @property
    def hostport(self):
        return self._dep_tchannel.hostport

    def register(self, scheme, endpoint=None, handler=None, **kwargs):

        def decorator(fn):

            assert handler is None, "can't handler when using as decorator"

            if endpoint is None:
                e = fn.__name__
            else:
                e = endpoint

            return self._dep_tchannel.register(
                endpoint=e,
                scheme=scheme,
                handler=fn,
                **kwargs
            )

        if handler is None:
            return decorator
        else:
            return decorator(handler)

    def advertise(self, routers, name=None, timeout=None):
        return self._dep_tchannel.advertise(
            routers=routers,
            name=name,
            timeout=timeout
        )
