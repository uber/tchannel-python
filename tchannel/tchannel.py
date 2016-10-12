# Copyright (c) 2016 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json
import logging

from threading import Lock

from tornado import gen

from . import schemes
from . import transport
from . import retry
from . import tracing
from .errors import AlreadyListeningError
from .glossary import DEFAULT_TIMEOUT
from .health import health
from .health import Meta
from .response import Response, TransportHeaders
from .tornado import TChannel as DeprecatedTChannel
from .tornado.dispatch import RequestDispatcher as DeprecatedDispatcher
from .tracing import TracingContextProvider

log = logging.getLogger('tchannel')

__all__ = ['TChannel']


class TChannel(object):
    """Manages connections and requests to other TChannel services.

    Usage for a JSON client/server:

    .. code:: python

        tchannel = TChannel(name='foo')

        @tchannel.json.register
        def handler(request):
            return {'foo': 'bar'}

        response = yield tchannel.json(
            service='some-service',
            endpoint='endpoint',
            headers={'req': 'headers'},
            body={'req': 'body'},
        )

    :cvar thrift:
        Make Thrift requests over TChannel and register Thrift handlers.
    :vartype thrift: ThriftArgScheme

    :cvar json:
        Make JSON requests over TChannel and register JSON handlers.
    :vartype json: JsonArgScheme

    :cvar raw:
        Make requests and register handles that pass raw bytes.
    :vartype raw: RawArgScheme

    """

    FALLBACK = DeprecatedTChannel.FALLBACK

    def __init__(self, name, hostport=None, process_name=None,
                 known_peers=None, trace=True, reuse_port=False,
                 context_provider=None, tracer=None):
        """
        **Note:** In general only one ``TChannel`` instance should be used at a
        time. Multiple ``TChannel`` instances are not advisable and could
        result in undefined behavior.

        :param string name:
            How this application identifies itself. This is the name callers
            will use to make contact, it is also what your downstream services
            will see in their metrics.

        :param string hostport:
            An optional host/port to serve on, e.g., ``"127.0.0.1:5555``. If
            not provided an ephemeral port will be used. When advertising on
            Hyperbahn you callers do not need to know your port.
        """
        assert name, 'service name cannot be empty or None'

        self.context_provider = context_provider or TracingContextProvider()

        # until we move everything here,
        # lets compose the old tchannel
        self._dep_tchannel = DeprecatedTChannel(
            name=name,
            hostport=hostport,
            process_name=process_name,
            known_peers=known_peers,
            trace=trace,
            tracer=tracer,
            dispatcher=DeprecatedDispatcher(_handler_returns_response=True),
            reuse_port=reuse_port,
            _from_new_api=True,
            context_provider_fn=lambda: self.context_provider,
        )

        self.name = name

        # set arg schemes
        self.raw = schemes.RawArgScheme(self)
        self.json = schemes.JsonArgScheme(self)
        self.thrift = schemes.ThriftArgScheme(self)
        self._listen_lock = Lock()
        # register default health endpoint
        self.thrift.register(Meta)(health)

        # advertise_response is the Future containing the response of calling
        # advertise().
        self._advertise_response = None
        self._advertise_lock = Lock()
        tracing.api_check(tracer=tracer)

    def is_listening(self):
        return self._dep_tchannel.is_listening()

    @property
    def hooks(self):
        return self._dep_tchannel.hooks

    @property
    def tracer(self):
        return self._dep_tchannel.tracer

    @gen.coroutine
    def call(
        self,
        scheme,
        service,
        arg1,
        arg2=None,
        arg3=None,
        timeout=None,
        retry_on=None,
        retry_limit=None,
        routing_delegate=None,
        hostport=None,
        shard_key=None,
        tracing_span=None,
        trace=None,  # to trace or not, defaults to self._dep_tchannel.trace
        caller_name=None,
    ):
        """Make low-level requests to TChannel services.

        **Note:** Usually you would interact with a higher-level arg scheme
        like :py:class:`tchannel.schemes.JsonArgScheme` or
        :py:class:`tchannel.schemes.ThriftArgScheme`.
        """

        # TODO - don't use asserts for public API
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

        tracing.apply_trace_flag(tracing_span, trace, self._dep_tchannel.trace)

        # calls tchannel.tornado.peer.PeerClientOperation.__init__
        operation = self._dep_tchannel.request(
            service=service,
            hostport=hostport,
            arg_scheme=scheme,
            retry=retry_on,
            tracing_span=tracing_span
        )

        # fire operation
        transport_headers = {
            transport.SCHEME: scheme,
            transport.CALLER_NAME: caller_name or self.name,
        }
        if shard_key:
            transport_headers[transport.SHARD_KEY] = shard_key
        if routing_delegate:
            transport_headers[transport.ROUTING_DELEGATE] = routing_delegate

        response = yield operation.send(
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            headers=transport_headers,
            retry_limit=retry_limit,
            ttl=timeout,
        )

        # unwrap response
        body = yield response.get_body()
        headers = yield response.get_header()
        t = TransportHeaders.from_dict(response.headers)
        result = Response(
            body=body,
            headers=headers,
            transport=t,
            status=response.code,
        )

        raise gen.Return(result)

    def listen(self, port=None):
        with self._listen_lock:
            if self._dep_tchannel.is_listening():
                listening_port = int(self.hostport.rsplit(":")[1])
                if port and port != listening_port:
                    raise AlreadyListeningError(
                        "TChannel server is already listening on port: %d"
                        % listening_port
                    )
                else:
                    return
            return self._dep_tchannel.listen(port)

    @property
    def host(self):
        return self._dep_tchannel.host

    @property
    def hostport(self):
        return self._dep_tchannel.hostport

    @property
    def port(self):
        return self._dep_tchannel.port

    def is_closed(self):
        return self._dep_tchannel.closed

    def close(self):
        return self._dep_tchannel.close()

    def register(self, scheme, endpoint=None, handler=None, **kwargs):
        if scheme is self.FALLBACK:
            # scheme is not required for fallback endpoints
            endpoint = scheme
            scheme = None

        def decorator(fn):

            # assert handler is None, "can't handler when using as decorator"

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

    def advertise(self, routers=None, name=None, timeout=None,
                  router_file=None, jitter=None):
        """Advertise with Hyperbahn.

        After a successful advertisement, Hyperbahn will establish long-lived
        connections with your application. These connections are used to load
        balance inbound and outbound requests to other applications on the
        Hyperbahn network.

        Re-advertisement happens periodically after calling this method (every
        minute). Hyperbahn will eject us from the network if it doesn't get a
        re-advertise from us after 5 minutes.

        This function may be called multiple times if it fails. If it
        succeeds, all consecutive calls are ignored.

        :param list routers:
            A seed list of known Hyperbahn addresses to attempt contact with.
            Entries should be of the form ``"host:port"``.

        :param string name:
            The name your application identifies itself as. This is usually
            unneeded because in the common case it will match the ``name`` you
            initialized the ``TChannel`` instance with. This is the identifier
            other services will use to make contact with you.

        :param timeout:
            The timeout (in sec) for the initial advertise attempt.
            Defaults to 30 seconds.

        :param jitter:
            Variance allowed in the interval per request. Defaults to 5
            seconds.  The jitter applies to the initial advertise request as
            well.

        :param router_file:
            The host file that contains the routers information. The file
            should contain a JSON stringified format of the routers parameter.
            Either routers or router_file should be provided. If both provided,
            a ValueError will be raised.

        :returns:
            A future that resolves to the remote server's response after the
            first advertise finishes.

        :raises TimeoutError:
            When unable to make our first advertise request to Hyperbahn.
            Subsequent requests may fail but will be ignored.
        """
        if routers is not None and router_file is not None:
            raise ValueError(
                'Only one of routers and router_file can be provided.')

        if routers is None and router_file is not None:
            # should just let the exceptions fly
            try:
                with open(router_file, 'r') as json_data:
                    routers = json.load(json_data)
            except (IOError, OSError, ValueError):
                log.exception('Failed to read seed routers list.')
                raise

        @gen.coroutine
        def _advertise():
            result = yield self._dep_tchannel.advertise(
                routers=routers,
                name=name,
                timeout=timeout,
            )
            body = yield result.get_body()
            headers = yield result.get_header()
            response = Response(json.loads(body), headers or {})
            raise gen.Return(response)

        def _on_advertise(future):
            if not future.exception():
                return

            # If the request failed, clear the response so that we can try
            # again.
            with self._advertise_lock:
                # `is` comparison to ensure we're not deleting another Future.
                if self._advertise_response is future:
                    self._advertise_response = None

        with self._advertise_lock:
            if self._advertise_response is not None:
                return self._advertise_response
            future = self._advertise_response = _advertise()

        # We call add_done_callback here rather than when we call _advertise()
        # because if the future has already resolved by the time we call
        # add_done_callback, the callback will immediately be executed. The
        # callback will try to acquire the advertise_lock which we already
        # hold and end up in a deadlock.
        future.add_done_callback(_on_advertise)
        return future
