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

import sys
import logging

from collections import deque
from itertools import takewhile, dropwhile

from tchannel import tracing
from tchannel.tracing import ClientTracer
from tornado import gen
from tornado.iostream import StreamClosedError

from ..schemes import DEFAULT as DEFAULT_SCHEME
from ..retry import (
    DEFAULT as DEFAULT_RETRY, DEFAULT_RETRY_LIMIT
)
from ..errors import NoAvailablePeerError
from ..errors import TChannelError
from ..errors import NetworkError
from ..event import EventType
from ..glossary import DEFAULT_TIMEOUT
from ..peer_heap import PeerHeap
from ..peer_strategy import PreferIncomingCalculator
from .connection import StreamConnection
from .connection import INCOMING, OUTGOING
from .request import Request
from .stream import InMemStream
from .stream import read_full
from .stream import maybe_stream

log = logging.getLogger('tchannel')


class Peer(object):
    """A Peer manages connections to or from a specific host-port."""

    __slots__ = (
        'tchannel',
        'host',
        'port',

        'rank',
        'index',
        'order',
        'chosen_count',
        'on_conn_change',
        'connections',

        '_connecting',
        '_on_conn_change_cb',
    )

    # Class used to create new outgoing connections.
    #
    # It must support a .outgoing method.
    connection_class = StreamConnection

    def __init__(self, tchannel, hostport, rank=None, on_conn_change=None):
        """Initialize a Peer

        :param tchannel:
            TChannel through which requests will be made.
        :param hostport:
            Host-port this Peer is for.
        :param rank:
            The rank of a peer will affect the chance that the peer gets
            selected when the client sends outbound requests. Lower rank is
            better.
        :param on_conn_change:
            A callback method takes Peer object as input and is called whenever
            there are connection changes in the peer.
        """
        assert hostport, "hostport is required"

        self.tchannel = tchannel
        self.host, port = hostport.rsplit(':', 1)
        self.port = int(port)

        #: Collection of all connections for this Peer. Incoming connections
        #: are added to the left side of the deque and outgoing connections to
        #: the right side.
        self.connections = deque()

        # This contains a future to the TornadoConnection if we're already in
        # the process of making an outgoing connection to the peer. This
        # helps avoid making multiple outgoing connections.
        self._connecting = None

        # rank is used to measure the performance of the peer.
        # It will be used in the peer heap.
        if rank is not None:
            self.rank = rank
        else:
            self.rank = sys.maxint
        # index records the position of the peer in the peer heap
        self.index = -1
        # order maintains the push order of the peer in the heap.
        self.order = 0
        # for debug purpose, count the number of times the peer gets selected.
        self.chosen_count = 0

        # callback is called when there is a change in connections.
        self._on_conn_change_cb = on_conn_change

    def set_on_conn_change_callback(self, cb):
        self._on_conn_change_cb = cb

    def connect(self):
        """Get a connection to this peer.

        If an connection to the peer already exists (either incoming or
        outgoing), that's returned. Otherwise, a new outgoing connection to
        this peer is created.

        :return:
            A future containing a connection to this host.
        """
        # Prefer incoming connections over outgoing connections.
        if self.connections:
            # First value is an incoming connection
            future = gen.Future()
            future.set_result(self.connections[0])
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
                self.register_outgoing_conn(connection)
            self._connecting = None

        conn_future.add_done_callback(on_connect)
        return conn_future

    def _set_on_close_cb(self, conn):

        def on_close():
            self.connections.remove(conn)
            self._on_conn_change()

        conn.set_close_callback(on_close)

    @property
    def has_incoming_connections(self):
        return self.connections and self.connections[0].direction == INCOMING

    def register_outgoing_conn(self, conn):
        """Add outgoing connection into the heap."""
        assert conn, "conn is required"
        conn.set_outbound_pending_change_callback(self._on_conn_change)
        self.connections.append(conn)
        self._set_on_close_cb(conn)
        self._on_conn_change()

    def register_incoming_conn(self, conn):
        """Add incoming connection into the heap."""
        assert conn, "conn is required"
        conn.set_outbound_pending_change_callback(self._on_conn_change)
        self.connections.appendleft(conn)
        self._set_on_close_cb(conn)
        self._on_conn_change()

    def _on_conn_change(self):
        """Function will be called any time there is connection changes."""
        if self._on_conn_change_cb:
            self._on_conn_change_cb(self)

    @property
    def hostport(self):
        """The host-port this Peer is for."""
        return "%s:%d" % (self.host, self.port)

    @property
    def outgoing_connections(self):
        """Returns a list of all outgoing connections for this peer."""

        # Outgoing connections are on the right
        return list(
            dropwhile(lambda c: c.direction != OUTGOING, self.connections)
        )

    @property
    def incoming_connections(self):
        """Returns a list of all incoming connections for this peer."""

        # Incoming connections are on the left.
        return list(
            takewhile(lambda c: c.direction == INCOMING, self.connections)
        )

    @property
    def total_outbound_pendings(self):
        """Return the total number of out pending req/res among connections"""
        return sum(c.total_outbound_pendings for c in self.connections)

    @property
    def is_ephemeral(self):
        """Whether this Peer is ephemeral."""
        return self.host == '0.0.0.0' or self.port == 0

    @property
    def connected(self):
        """Return True if this Peer is connected."""

        return len(self.connections) > 0

    def close(self):
        for connection in list(self.connections):
            # closing the connection will mutate the deque so create a copy
            connection.close()


class PeerClientOperation(object):
    """Encapsulates client operations that can be performed against a peer."""

    def __init__(self,
                 peer_group,
                 service,
                 arg_scheme=None,
                 retry=None,
                 tracing_span=None,
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
        :param tracing_span
            tracing span created for this request
        :param hostport
            remote server's host port.
        """
        assert peer_group, "peer group must not be None"
        service = service or ''

        self.peer_group = peer_group
        self.tchannel = peer_group.tchannel
        self.service = service
        self.tracing_span = tracing_span

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
            Headers will be put in the message as protocol header.
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

        # set default transport headers
        headers = headers or {}
        for k, v in self.headers.iteritems():
            headers.setdefault(k, v)

        if self.tracing_span is None:
            tracer = ClientTracer(channel=self.tchannel)
            self.tracing_span, _ = tracer.start_span(
                service=self.service, endpoint=endpoint,
                hostport=self._hostport, encoding=self.headers.get('as')
            )

        request = Request(
            service=self.service,
            argstreams=[InMemStream(endpoint), arg2, arg3],
            id=connection.writer.next_message_id(),
            headers=headers,
            endpoint=endpoint,
            ttl=ttl,
            tracing=tracing.span_to_tracing_field(self.tracing_span)
        )

        # only retry on non-stream request
        if request.is_streaming_request or self._hostport:
            retry_limit = 0

        if request.is_streaming_request:
            request.ttl = 0

        try:
            with self.tracing_span:  # to ensure span is finished
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

        try:
            response = yield response_future
        except StreamClosedError as error:
            network_error = NetworkError(
                id=req.id,
                description=error.message,
                tracing=req.tracing,
            )
            # event: after_receive_error
            self.tchannel.event_emitter.fire(
                EventType.after_receive_error, req, error,
            )
            raise network_error
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
            except TChannelError:
                (typ, error, tb) = sys.exc_info()
                try:
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
                        raise typ, error, tb
                finally:
                    del tb  # for GC

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
        request.rewind(connection.writer.next_message_id())

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
        'peer_heap',
        'rank_calculator',
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

        self.peer_heap = PeerHeap()
        self.rank_calculator = PreferIncomingCalculator()

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
            self.add(hostport)

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
        peer = self._peers.pop(hostport, None)
        if peer:
            self.peer_heap.remove_peer(peer)
        return peer

    def add(self, peer):
        """Add an existing Peer to this group.

        A peer for the given host-port must not already exist in the group.
        """
        assert peer, "peer is required"

        if isinstance(peer, basestring):
            # Assume strings are host-ports
            peer = self.peer_class(
                tchannel=self.tchannel,
                hostport=peer,
                on_conn_change=self._update_heap,
            )

        assert peer.hostport not in self._peers, (
            "%s already has a peer" % peer.hostport
        )
        peer.rank = self.rank_calculator.get_rank(peer)
        self._peers[peer.hostport] = peer
        self.peer_heap.add_and_shuffle(peer)

    def _update_heap(self, peer):
        """Recalculate the peer's rank and update itself in the peer heap."""
        rank = self.rank_calculator.get_rank(peer)
        if rank == peer.rank:
            return

        peer.rank = rank
        self.peer_heap.update_peer(peer)

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

        return self.peer_heap.smallest_peer(
            (lambda p: p.hostport not in blacklist and not p.is_ephemeral),
        )
