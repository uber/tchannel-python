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

from __future__ import absolute_import

import inspect
import logging

import opentracing
import os
import socket
import sys
from functools import partial

import tornado.gen
import tornado.ioloop
import tornado.iostream
import tornado.tcpserver
from tornado.netutil import bind_sockets

from . import hyperbahn
from ..deprecate import deprecate
from ..enum import enum
from ..errors import AlreadyListeningError
from ..event import EventEmitter
from ..event import EventRegistrar
from ..glossary import (
    TCHANNEL_LANGUAGE,
    TCHANNEL_LANGUAGE_VERSION,
    TCHANNEL_VERSION,
)
from ..net import local_ip
from ..schemes import DEFAULT_NAMES
from ..schemes import JSON
from ..serializer.json import JsonSerializer
from ..serializer.raw import RawSerializer
from ..tracing import TracingContextProvider
from .connection import StreamConnection
from .connection import INCOMING
from .dispatch import RequestDispatcher
from .peer import PeerGroup

log = logging.getLogger('tchannel')


State = enum(
    'State',
    ready=0,
    closing=1,
    closed=2,
)


class TChannel(object):
    """Manages inbound and outbound connections to various hosts."""

    # TODO deprecate in favor of top-level tchannel.TChannel

    FALLBACK = RequestDispatcher.FALLBACK

    def __init__(self, name, hostport=None, process_name=None,
                 known_peers=None, trace=False, dispatcher=None,
                 reuse_port=False, context_provider_fn=None,
                 tracer=None, _from_new_api=False):
        """Build or re-use a TChannel.

        :param name:
            Name is used to identify client or service itself.

        :param hostport:
            The host-port at which the service behind this TChannel is
            reachable. The port specified in the ``hostport`` is what the
            server will listen on. If unspecified, the system will attempt to
            determine the local network IP for this host and use an
            OS-assigned port.

        :param process_name:
            Name of this process. This is used for logging only. If
            unspecified, this will default to ``$processName[$processId]``.

        :param known_peers:
            A list of host-ports at which already known peers can be reached.
            Defaults to an empty list.

        :param trace:
            Flag to turn on/off distributed tracing. It can be a bool
            variable or a function that return true or false.

        :param tracer:
            An instance of OpenTracing Tracer (http://opentracing.io).
            If not provided, a global `opentracing.tracer` will be used.

        :param context_provider_fn:
            A getter function to retrieve an instance of
            ``tracing.TracingContextProvider`` used to manage tracing span
            in a thread-local request context.
        """

        self._state = State.ready
        if context_provider_fn:
            self.context_provider_fn = context_provider_fn
        else:
            context_provider = TracingContextProvider()
            self.context_provider_fn = lambda: context_provider

        if not dispatcher:
            self._handler = RequestDispatcher()
        else:
            self._handler = dispatcher

        self.peers = PeerGroup(self)

        self._port = 0
        self._host = None
        if hostport:
            self._host, port = hostport.rsplit(':', 1)
            self._port = int(port)

        if not self._host:
            # TChannel(":4040") => determine IP automatically but use port
            # 4040
            self._host = local_ip()

        self.process_name = process_name or "%s[%s]" % (
            sys.argv[0], os.getpid()
        )

        self.name = name
        self._trace = trace
        self._tracer = tracer

        # register event hooks
        self.event_emitter = EventEmitter()
        self.hooks = EventRegistrar(self.event_emitter)

        if known_peers:
            for peer_hostport in known_peers:
                self.peers.add(peer_hostport)

        # server created from calling listen()
        self._server = None

        # allow SO_REUSEPORT
        self._reuse_port = reuse_port

        # warn if customers are still using this old and soon to be deleted api
        if _from_new_api is False:
            deprecate(
                "tchannel.tornado.TChannel is deprecated and will be removed" +
                " in a a future version - please switch usage to " +
                "tchannel.TChannel object. Thank you."
            )

    @property
    def trace(self):
        if callable(self._trace):
            return self._trace()
        else:
            return self._trace

    @property
    def tracer(self):
        if self._tracer:
            return self._tracer
        else:
            return opentracing.tracer

    @property
    def context_provider(self):
        return self.context_provider_fn()

    def advertise(
        self,
        routers=None,
        name=None,
        timeout=None,
        router_file=None,
        jitter=None,
    ):
        """Make a service available on the Hyperbahn routing mesh.

        This will make contact with a Hyperbahn host from a list of known
        Hyperbahn routers. Additional Hyperbahn connections will be established
        once contact has been made with the network.

        :param router:
            A seed list of addresses of Hyperbahn routers, e.g.,
            ``["127.0.0.1:23000"]``.

        :param name:
            The identity of this service on the Hyperbahn.

            This is usually unnecessary, as it defaults to the name given when
            initializing the :py:class:`TChannel` (which is used as your
            identity as a caller).

        :returns:
            A future that resolves to the remote server's response after
            the first advertise finishes.

            Advertisement will continue to happen periodically.
        """
        name = name or self.name

        if not self.is_listening():
            self.listen()

        return hyperbahn.advertise(
            self,
            name,
            routers,
            timeout,
            router_file,
            jitter,
        )

    @property
    def closed(self):
        return self._state == State.closed

    def close(self):
        if self._state in [State.closed, State.closing]:
            return

        self._state = State.closing
        try:
            self.peers.clear()
            if self._server:
                self._server.stop()
        finally:
            self._state = State.closed

    @property
    def host(self):
        return self._host

    @property
    def hostport(self):
        return "%s:%d" % (self._host, self._port)

    @property
    def port(self):
        return self._port

    def request(self,
                hostport=None,
                service=None,
                arg_scheme=None,
                retry=None,
                **kwargs):
        """Initiate a new request through this TChannel.

        :param hostport:
            Host to which the request will be made. If unspecified, a random
            known peer will be picked. This is not necessary if using
            Hyperbahn.

        :param service:
            The name of a service available on Hyperbahn. Defaults to an empty
            string.

        :param arg_scheme:
            Determines the serialization scheme for the request. One of 'raw',
            'json', or 'thrift'. Defaults to 'raw'.

        :param rety:
            One of 'n' (never retry), 'c' (retry on connection errors), 't'
            (retry on timeout), 'ct' (retry on connection errors and timeouts).

            Defaults to 'c'.
        """
        # TODO disallow certain parameters or don't propagate them backwards.
        # For example, blacklist and rank threshold aren't really
        # user-configurable right now.
        return self.peers.request(hostport=hostport,
                                  service=service,
                                  arg_scheme=arg_scheme,
                                  retry=retry,
                                  **kwargs)

    def listen(self, port=None):
        """Start listening for incoming connections.

        A request handler must have already been specified with
        ``TChannel.host``.

        :param port:
            An explicit port to listen on. This is unnecessary when advertising
            on Hyperbahn.

        :returns:
            Returns immediately.

        :raises AlreadyListeningError:
            If listen was already called.
        """

        if self.is_listening():
            raise AlreadyListeningError(
                "listen has already been called"
            )

        if port:
            assert not self._port, "Port has already been set."
            self._port = int(port)

        assert self._handler, "Call .host with a RequestHandler first"
        server = TChannelServer(self)

        bind_sockets_kwargs = {
            'port': self._port,
            # ipv6 causes random address already in use (socket.error w errno
            # == 98) when getaddrinfo() returns multiple values
            # @see https://github.com/uber/tchannel-python/issues/256
            'family': socket.AF_INET,
        }
        if self._reuse_port is True:
            # allow multiple processes to share the same port,
            # this is really useful in a world where services launch N
            # processes per container/os-space, where N is
            # the amount of cpus for example
            bind_sockets_kwargs['reuse_port'] = True

        sockets = bind_sockets(**bind_sockets_kwargs)
        assert sockets, "No sockets bound for port %d" % self._port

        # If port was 0, the OS probably assigned something better.
        self._port = sockets[0].getsockname()[1]

        server.add_sockets(sockets)

        # assign server so we don't listen twice
        self._server = server

    def is_listening(self):

        if self._server:
            return True

        return False

    def receive_call(self, message, connection):

        if not self._handler:
            log.warn(
                "Received %s but a handler has not been defined.", str(message)
            )
            return
        return self._handler.handle(message, connection)

    def _register_simple(self, endpoint, scheme, f):
        """Register a simple endpoint with this TChannel.

        :param endpoint:
            Name of the endpoint being registered.
        :param scheme:
            Name of the arg scheme under which the endpoint will be
            registered.
        :param f:
            Callable handler for the endpoint.
        """
        assert scheme in DEFAULT_NAMES, ("Unsupported arg scheme %s" % scheme)
        if scheme == JSON:
            req_serializer = JsonSerializer()
            resp_serializer = JsonSerializer()
        else:
            req_serializer = RawSerializer()
            resp_serializer = RawSerializer()
        self._handler.register(endpoint, f, req_serializer, resp_serializer)
        return f

    def _register_thrift(self, service_module, handler, **kwargs):
        """Register a Thrift endpoint on this TChannel.

        :param service_module:
            Reference to the Thrift-generated module for the service being
            registered.
        :param handler:
            Handler for the endpoint
        :param method:
            Name of the Thrift method being registered. If omitted, ``f``'s
            name is assumed to be the method name.
        :param service:
            Name of the Thrift service. By default this is determined
            automatically from the module name.
        """
        import tchannel.thrift as thrift
        # Imported inside the function so that we don't have a hard dependency
        # on the Thrift library. This function is usable only if the Thrift
        # library is installed.
        thrift.register(self._handler, service_module, handler, **kwargs)
        return handler

    def register(self, endpoint, scheme=None, handler=None, **kwargs):
        """Register a handler with this TChannel.

        This may be used as a decorator:

        .. code-block:: python

            app = TChannel(name='bar')

            @app.register("hello", "json")
            def hello_handler(request, response):
                params = yield request.get_body()

        Or as a function:

        .. code-block:: python

            # Here we have a Thrift handler for `Foo::hello`
            app.register(Foo, "hello", hello_thrift_handler)

        :param endpoint:
            Name of the endpoint being registered. This should be a reference
            to the Thrift-generated module if this is a Thrift endpoint. It
            may also be ``TChannel.FALLBACK`` if it's intended to be a
            catch-all endpoint.
        :param scheme:
            Name of the scheme under which the endpoint is being registered.
            One of "raw", "json", and "thrift". Defaults to "raw", except if
            "endpoint" was a module, in which case this defaults to "thrift".

        :param handler:
            If specified, this is the handler function. If ignored, this
            function returns a decorator that can be used to register the
            handler function.

        :returns:
            If ``handler`` was specified, this returns ``handler``. Otherwise,
            it returns a decorator that can be applied to a function to
            register it as the handler.
        """
        assert endpoint is not None, "endpoint is required"

        if endpoint is TChannel.FALLBACK:
            decorator = partial(self._handler.register, TChannel.FALLBACK)
            if handler is not None:
                return decorator(handler)
            else:
                return decorator

        if not scheme:
            # scheme defaults to raw, unless the endpoint is a service module.
            if inspect.ismodule(endpoint):
                scheme = "thrift"
            else:
                scheme = "raw"
        scheme = scheme.lower()
        if scheme == 'thrift':
            decorator = partial(self._register_thrift, endpoint, **kwargs)
        else:
            decorator = partial(
                self._register_simple, endpoint, scheme, **kwargs
            )

        if handler is not None:
            return decorator(handler)
        else:
            return decorator


class TChannelServer(tornado.tcpserver.TCPServer):
    __slots__ = ('tchannel',)

    def __init__(self, tchannel):
        super(TChannelServer, self).__init__()
        self.tchannel = tchannel

    @tornado.gen.coroutine
    def handle_stream(self, stream, address):
        log.debug("New incoming connection from %s:%d" % address)

        conn = StreamConnection(
            connection=stream,
            tchannel=self.tchannel,
            direction=INCOMING,
        )

        yield conn.expect_handshake(headers={
            'host_port': self.tchannel.hostport,
            'process_name': self.tchannel.process_name,
            'tchannel_language': TCHANNEL_LANGUAGE,
            'tchannel_language_version': TCHANNEL_LANGUAGE_VERSION,
            'tchannel_version': TCHANNEL_VERSION,
        })

        log.debug(
            "Successfully completed handshake with %s:%s (%s)",
            conn.remote_host,
            conn.remote_host_port,
            conn.remote_process_name)

        self.tchannel.peers.get(
            "%s:%s" % (conn.remote_host,
                       conn.remote_host_port)
        ).register_incoming_conn(conn)

        yield conn.serve(handler=self._handle)

    def _handle(self, message, connection):
        self.tchannel.receive_call(message, connection)
