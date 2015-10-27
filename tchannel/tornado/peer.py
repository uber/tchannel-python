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

import logging
import random
from collections import deque
from itertools import takewhile, dropwhile
from tornado import gen

from ..schemes import DEFAULT as DEFAULT_SCHEME
from ..retry import (
    DEFAULT as DEFAULT_RETRY, DEFAULT_RETRY_LIMIT
)
from tchannel.event import EventType
from tchannel.glossary import DEFAULT_TIMEOUT
from ..context import get_current_context
from ..errors import NoAvailablePeerError
from ..errors import TChannelError
from ..errors import NetworkError
from ..zipkin.annotation import Endpoint
from ..zipkin.trace import Trace
from .connection import StreamConnection
from .connection import INCOMING, OUTGOING
from .request import Request
from .stream import InMemStream
from .stream import read_full
from .stream import maybe_stream
from .timeout import timeout

log = logging.getLogger('tchannel')


class Peer(object):
    """A Peer manages connections to or from a specific host-port."""

    __slots__ = (
        'tchannel',
        'host',
        'port',

        '_connections',
        '_connecting',
    )

    # Class used to create new outgoing connections.
    #
    # It must support a .outgoing method.
    connection_class = StreamConnection

    def __init__(self, tchannel, hostport):
        """Initialize a Peer

        :param tchannel:
            TChannel through which requests will be made.
        :param hostport:
            Host-port this Peer is for.
        """
        assert hostport, "hostport is required"

        self.tchannel = tchannel
        self.host, port = hostport.rsplit(':', 1)
        self.port = int(port)

        #: Collection of all connections for this Peer. Incoming connections
        #: are added to the left side of the deque and outgoing connections to
        #: the right side.
        self._connections = deque()

        # This contains a future to the TornadoConnection if we're already in
        # the process of making an outgoing connection to the peer. This
        # helps avoid making multiple outgoing connections.
        self._connecting = None

    def connect(self):
        """Get a connection to this peer.

        If an connection to the peer already exists (either incoming or
        outgoing), that's returned. Otherwise, a new outgoing connection to
        this peer is created.

        :return:
            A future containing a connection to this host.
        """
        # Prefer incoming connections over outgoing connections.
        if self._connections:
            # First value is an incoming connection
            future = gen.Future()
            future.set_result(self._connections[0])
            return future

        if self._connecting:
            # If we're in the process of connecting to the peer, just wait
            # and re-use that connection.
            return self._connecting

        conn_future = self._connecting = self.connection_class.outgoing(
            hostport=self.hostport,
            process_name=self.tchannel.process_name,
            serve_hostport=self.tchannel.hostport,
            handler=self.tchannel.receive_call,
            tchannel=self.tchannel,
        )

        def on_connect(_):
            if not conn_future.exception():
                # We don't actually need to handle the exception. That's on
                # the caller.
                connection = conn_future.result()
                self._connections.append(connection)
                self._set_on_close_cb(connection)
            self._connecting = None

        conn_future.add_done_callback(on_connect)
        return conn_future

    def _set_on_close_cb(self, conn):

        def on_close():
            self._connections.remove(conn)

        conn.set_close_callback(on_close)

    def register_incoming(self, conn):
        assert conn, "conn is required"
        self._connections.appendleft(conn)
        self._set_on_close_cb(conn)

    @property
    def hostport(self):
        """The host-port this Peer is for."""
        return "%s:%d" % (self.host, self.port)

    @property
    def connections(self):
        """Returns an iterator over all connections for this peer.

        Incoming connections are listed first."""
        return list(self._connections)

    @property
    def outgoing_connections(self):
        """Returns a list of all outgoing connections for this peer."""

        # Outgoing connections are on the right
        return list(
            dropwhile(lambda c: c.direction != OUTGOING, self._connections)
        )

    @property
    def incoming_connections(self):
        """Returns a list of all incoming connections for this peer."""

        # Incoming connections are on the left.
        return list(
            takewhile(lambda c: c.direction == INCOMING, self._connections)
        )

    @property
    def is_ephemeral(self):
        """Whether this Peer is ephemeral."""
        return self.host == '0.0.0.0' and self.port == 0

    @property
    def connected(self):
        """Return True if this Peer is connected."""

        return len(self._connections) > 0

    def close(self):
        for connection in list(self._connections):
            # closing the connection will mutate the deque so create a copy
            connection.close()


class PeerClientOperation(object):
    """Encapsulates client operations that can be performed against a peer."""

    def __init__(self,
                 peer_group,
                 service,
                 arg_scheme=None,
                 retry=None,
                 parent_tracing=None,
                 hostport=None):
        """Initialize a new PeerClientOperation.

        :param peer_group:
            instance of PeerGroup that maintain all peers.
        :param service:
            Name of the service being called through this peer. Defaults to
            an empty string.
        :param arg_scheme
            arg scheme type
        :param retry
            retry type
        :param parent_tracing
            tracing span from parent request
        :param hostport
            remote server's host port.
        """
        assert peer_group, "peer group must not be None"
        service = service or ''

        self.peer_group = peer_group
        self.tchannel = peer_group.tchannel
        self.service = service
        self.parent_tracing = parent_tracing
        if not self.parent_tracing and get_current_context():
            self.parent_tracing = get_current_context().parent_tracing

        # TODO the term headers are reserved for application headers,
        # these are transport headers,
        self.headers = {
            'as': arg_scheme or DEFAULT_SCHEME,
            're': retry or DEFAULT_RETRY,
            'cn': self.tchannel.name,
        }

        # keep all arguments for retry purpose.
        # not retry if hostport is set.
        self._hostport = hostport

    def _choose(self, blacklist=None):
        peer = self.peer_group.choose(
            hostport=self._hostport,
            blacklist=blacklist,
        )
        return peer

    @gen.coroutine
    def _get_peer_connection(self, blacklist=None):
        """Find a peer and connect to it.

        Returns a ``(peer, connection)`` tuple.

        Raises ``NoAvailablePeerError`` if no healthy peers are found.

        :param blacklist:
            If given, a set of hostports for peers that we must not try.
        """

        blacklist = blacklist or set()

        peer = None
        connection = None

        while connection is None:
            peer = self._choose(blacklist)

            if not peer:
                raise NoAvailablePeerError(
                    "Can't find an available peer for '%s'" % self.service
                )

            try:
                connection = yield peer.connect()
            except NetworkError as e:
                log.info(
                    'Failed to connect to %s. Trying a different host.',
                    peer.hostport,
                    exc_info=e,
                )
                connection = None
                blacklist.add(peer.hostport)

        raise gen.Return((peer, connection))

    @gen.coroutine
    def send(
        self, arg1, arg2, arg3,
        headers=None,
        traceflag=None,
        retry_limit=None,
        ttl=None,
    ):
        """Make a request to the Peer.

        :param arg1:
            String or Stream containing the contents of arg1. If None, an empty
            stream is used.
        :param arg2:
            String or Stream containing the contents of arg2. If None, an empty
            stream is used.
        :param arg3:
            String or Stream containing the contents of arg3. If None, an empty
            stream is used.
        :param headers:
            Headers will be put int he message as protocol header.
        :param traceflag:
            Flag is for tracing.
        :param retry_limit:
           Maximum number of retries will perform on the message. If the number
           is 0, it means no retry.
        :param ttl:
            Timeout for each request (second).
        :return:
            Future that contains the response from the peer.
        """

        # find a peer connection
        # If we can't find available peer at the first time, we throw
        # NoAvailablePeerError. Later during retry, if we can't find available
        # peer, we throw exceptions from retry not NoAvailablePeerError.
        peer, connection = yield self._get_peer_connection()

        arg1, arg2, arg3 = (
            maybe_stream(arg1), maybe_stream(arg2), maybe_stream(arg3)
        )

        if retry_limit is None:
            retry_limit = DEFAULT_RETRY_LIMIT

        ttl = ttl or DEFAULT_TIMEOUT
        # hack to get endpoint from arg_1 for trace name
        arg1.close()
        endpoint = yield read_full(arg1)

        # TODO after adding stackcontext, get ride of this.
        if self.parent_tracing:
            parent_span_id = self.parent_tracing.span_id
            trace_id = self.parent_tracing.trace_id
        else:
            parent_span_id = None
            trace_id = None

        if traceflag is None:
            traceflag = self.tchannel.trace

        traceflag = traceflag() if callable(traceflag) else traceflag

        # set default transport headers
        headers = headers or {}
        for k, v in self.headers.iteritems():
            headers.setdefault(k, v)

        request = Request(
            service=self.service,
            argstreams=[InMemStream(endpoint), arg2, arg3],
            id=connection.next_message_id(),
            headers=headers,
            endpoint=endpoint,
            ttl=ttl,
            tracing=Trace(
                name=endpoint,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                endpoint=Endpoint(peer.host, peer.port, self.service),
                traceflags=traceflag,
            )
        )

        # only retry on non-stream request
        if request.is_streaming_request or self._hostport:
            retry_limit = 0

        if request.is_streaming_request:
            request.ttl = 0

        try:
            response = yield self.send_with_retry(
                request, peer, retry_limit, connection
            )
        except Exception as e:
            # event: on_exception
            self.tchannel.event_emitter.fire(
                EventType.on_exception, request, e,
            )
            raise

        log.debug("Got response %s", response)

        raise gen.Return(response)

    @gen.coroutine
    def _send(self, connection, req):
        # event: send_request
        self.tchannel.event_emitter.fire(EventType.before_send_request, req)
        response_future = connection.send_request(req)

        with timeout(response_future, req.ttl):
            try:
                response = yield response_future
            except TChannelError as error:
                # event: after_receive_error
                self.tchannel.event_emitter.fire(
                    EventType.after_receive_error, req, error,
                )
                raise
        # event: after_receive_response
        self.tchannel.event_emitter.fire(
            EventType.after_receive_response, req, response,
        )
        raise gen.Return(response)

    @gen.coroutine
    def send_with_retry(self, request, peer, retry_limit, connection):
        # black list to record all used peers, so they aren't chosen again.
        blacklist = set()
        for num_of_attempt in range(retry_limit + 1):
            try:
                response = yield self._send(connection, request)
                raise gen.Return(response)
            # Why are we retying on all errors????
            except TChannelError as error:
                blacklist.add(peer.hostport)
                (peer, connection) = yield self._prepare_for_retry(
                    request=request,
                    connection=connection,
                    protocol_error=error,
                    blacklist=blacklist,
                    num_of_attempt=num_of_attempt,
                    max_retry_limit=retry_limit,
                )

                if not connection:
                    raise error

    @gen.coroutine
    def _prepare_for_retry(
        self,
        request,
        connection,
        protocol_error,
        blacklist,
        num_of_attempt,
        max_retry_limit,
    ):

        self.clean_up_outgoing_request(request, connection, protocol_error)
        if not self.should_retry(request, protocol_error,
                                 num_of_attempt, max_retry_limit):
            raise gen.Return((None, None))

        result = yield self.prepare_next_request(request, blacklist)
        raise gen.Return(result)

    @gen.coroutine
    def prepare_next_request(self, request, blacklist):
        # find new peer
        peer = self._choose(blacklist=blacklist,)

        # no peer is available
        if not peer:
            raise gen.Return((None, None))

        connection = yield peer.connect()
        # roll back request
        request.rewind(connection.next_message_id())

        raise gen.Return((peer, connection))

    @staticmethod
    def should_retry(request, error, num_of_attempt, max_retry_limit):
        return (
            request.should_retry_on_error(error) and
            num_of_attempt != max_retry_limit
        )

    @staticmethod
    def clean_up_outgoing_request(request, connection, error):
        # stop the outgoing request
        request.set_exception(error)
        # remove from pending request list
        connection.remove_outstanding_request(request)


class PeerGroup(object):
    """A PeerGroup represents a collection of Peers.

    Requests routed through a PeerGroup can be sent to either a specific peer
    or a peer chosen at random.
    """

    peer_class = Peer

    __slots__ = (
        'tchannel',
        '_peers',
        '_resetting',
        '_reset_condition',
    )

    def __init__(self, tchannel):
        """Initializes a new PeerGroup.

        :param tchannel:
            TChannel used for communication by this PeerGroup
        """
        self.tchannel = tchannel

        # Dictionary from hostport to Peer.
        self._peers = {}

        # Notified when a reset is performed. This allows multiple coroutines
        # to block on the same reset.
        self._resetting = False

        # We'll create a Condition here later. We want to avoid it right now
        # because it has a side-effect of scheduling some dummy work on the
        # ioloop, which prevents us from forking (if you're into that).
        self._reset_condition = None

    def __str__(self):
        return "<PeerGroup peers=%s>" % str(self._peers)

    def clear(self):
        """Reset this PeerGroup.

        This closes all connections to all known peers and forgets about
        these peers.

        :returns:
            A Future that resolves with a value of None when the operation
            has finished
        """
        try:
            for peer in self._peers.values():
                peer.close()
        finally:
            self._peers = {}
            self._resetting = False

    def get(self, hostport):
        """Get a Peer for the given destination.

        A new Peer is added and returned if one does not already exist for the
        given host-port. Otherwise, the existing Peer is returned.
        """
        assert hostport, "hostport is required"
        if hostport not in self._peers:
            self._peers[hostport] = self.peer_class(self.tchannel, hostport)
        return self._peers[hostport]

    def lookup(self, hostport):
        """Look up a Peer for the given host and port.

        Returns None if a Peer for the given host-port does not exist.
        """
        assert hostport, "hostport is required"
        return self._peers.get(hostport, None)

    def remove(self, hostport):
        """Delete the Peer for the given host port.

        Does nothing if a matching Peer does not exist.

        :returns: The removed Peer
        """
        assert hostport, "hostport is required"
        return self._peers.pop(hostport, None)

    def add(self, peer):
        """Add an existing Peer to this group.

        A peer for the given host-port must not already exist in the group.
        """
        assert peer, "peer is required"

        if isinstance(peer, basestring):
            # Assume strings are host-ports
            peer = self.peer_class(self.tchannel, peer)

        assert peer.hostport not in self._peers, (
            "%s already has a peer" % peer.hostport
        )

        self._peers[peer.hostport] = peer

    @property
    def hosts(self):
        """Get all host-ports managed by this PeerGroup."""
        return self._peers.keys()

    @property
    def peers(self):
        """Get all Peers managed by this PeerGroup."""
        return self._peers.values()

    def request(self, service, hostport=None, **kwargs):
        """Initiate a new request through this PeerGroup.

        :param hostport:
            If specified, requests will be sent to the specific host.
            Otherwise, a known peer will be picked at random.
        :param service:
            Name of the service being called. Defaults to an empty string.
        """
        return PeerClientOperation(
            peer_group=self,
            service=service,
            hostport=hostport,
            **kwargs)

    def _connected_peers(self, hostports):
        for hostport in hostports:
            peer = self.get(hostport)
            if peer.connected:
                yield peer

    def choose(self, hostport=None, blacklist=None):
        """Choose a Peer that matches the given criteria.

        :param hostport:
            Specifies that the returned Peer must be for the given host-port.
            Without this, all peers managed by this PeerGroup are
            candidates.
        :param blacklist:
            Peers on the blacklist won't be chosen.
        :returns:
            A Peer that matches all the requested criteria or None if no such
            Peer was found.
        """

        blacklist = blacklist or set()
        if hostport:
            return self.get(hostport)

        hosts = self._peers.viewkeys() - blacklist
        if not hosts:
            return None

        peers = list(self._connected_peers(hosts))
        if peers:
            return peers[random.randint(0, len(peers)-1)]
        else:
            hosts = list(hosts)
            host = hosts[random.randint(0, len(hosts)-1)]
            return self.get(host)
