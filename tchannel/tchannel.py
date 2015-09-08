# Copyright (c) 2015 Uber Technologies, Inc.
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

from tornado import gen

from . import schemes
from . import transport
from . import retry
from .glossary import DEFAULT_TIMEOUT
from .response import Response, TransportHeaders
from .tornado import TChannel as DeprecatedTChannel
from .tornado.dispatch import RequestDispatcher as DeprecatedDispatcher

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

    def __init__(self, name, hostport=None, process_name=None,
                 known_peers=None, trace=False):
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

    def is_listening(self):
        return self._dep_tchannel.is_listening()

    @property
    def hooks(self):
        return self._dep_tchannel.hooks

    @gen.coroutine
    def call(self, scheme, service, arg1, arg2=None, arg3=None,
             timeout=None, retry_on=None, retry_limit=None, hostport=None):
        """Make low-level requests to TChannel services.

        **Note:** Usually you would interact with a higher-level arg scheme
        like :py:class:`tchannel.schemes.JsonArgScheme` or
        :py:class:`tchannel.schemes.ThriftArgScheme`.
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
            retry_limit=retry_limit,
            ttl=timeout,
        )

        # unwrap response
        body = yield response.get_body()
        headers = yield response.get_header()
        t = transport.to_kwargs(response.headers)
        t = TransportHeaders(**t)
        result = Response(
            body=body,
            headers=headers,
            transport=t
        )

        raise gen.Return(result)

    def listen(self, port=None, backlog=2048):
        return self._dep_tchannel.listen(port, backlog)

    @property
    def hostport(self):
        return self._dep_tchannel.hostport

    def register(self, scheme, endpoint=None, handler=None, **kwargs):

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

    @gen.coroutine
    def advertise(self, routers=None, name=None, timeout=None,
                  router_file=None):
        """Advertise with Hyperbahn.

        After a successful advertisement, Hyperbahn will establish long-lived
        connections with your application. These connections are used to load
        balance inbound and outbound requests to other applications on the
        Hyperbahn network.

        Re-advertisement happens periodically after calling this method (every
        minute). Hyperbahn will eject us from the network if it doesn't get a
        re-advertise from us after 5 minutes.

        :param list routers:
            A seed list of known Hyperbahn addresses to attempt contact with.
            Entries should be of the form ``"host:port"``.

        :param string name:
            The name your application identifies itself as. This is usually
            unneeded because in the common case it will match the ``name`` you
            initialized the ``TChannel`` instance with. This is the identifier
            other services will use to make contact with you.

        :param timeout:
            The timeout (in seconds) for the initial advertise attempt.
            Defaults to 30 seconds.

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

        dep_result = yield self._dep_tchannel.advertise(
            routers=routers,
            name=name,
            timeout=timeout
        )

        body = yield dep_result.get_body()
        headers = yield dep_result.get_header()
        response = Response(json.loads(body), headers or {})

        raise gen.Return(response)
