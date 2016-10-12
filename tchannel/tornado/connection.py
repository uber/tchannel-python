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

import logging
import os
import socket
import sys

import tornado.gen
import tornado.iostream

from tornado import stack_context
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError

from .. import errors
from .. import frame
from .. import messages
from .. import _queue as queues
from .._future import fail_to
from ..errors import NetworkError
from ..errors import TChannelError
from ..event import EventType
from ..glossary import (
    TCHANNEL_LANGUAGE,
    TCHANNEL_LANGUAGE_VERSION,
    TCHANNEL_VERSION,
    MAX_MESSAGE_ID,
)
from ..io import BytesIO
from ..messages.common import PROTOCOL_VERSION
from ..messages.common import FlagsType
from ..messages.common import StreamState
from ..messages.types import Types
from .message_factory import build_raw_error_message
from .message_factory import MessageFactory
from .tombstone import Cemetery

log = logging.getLogger('tchannel')


#: Sentinel object representing that the connection is outgoing.
OUTGOING = object()

#: Sentinel object representing that the connection is incoming.
INCOMING = object()


class TornadoConnection(object):
    """Manages a bi-directional TChannel conversation between two machines.

    The following primary bi-directional operations are provided:

    ``write(message)``
        Send the message up the wire.
    ``await(message)``
        Receive a message.
    ``send(message)``
        Send a message and receive its response.

    In addition to those, the following operations are provided and should be
    used depending on the direction of the connection.

    ``initiate_handshake``
        Perform a handshake with the remote host.
    ``expect_handshake``
        Expect a handshake request from the remote host.
    """

    CALL_REQ_TYPES = frozenset([Types.CALL_REQ, Types.CALL_REQ_CONTINUE])
    CALL_RES_TYPES = frozenset([Types.CALL_RES, Types.CALL_RES_CONTINUE])

    def __init__(self, connection, tchannel=None, direction=None):
        assert connection, "connection is required"

        self.closed = False
        self.connection = connection
        self.direction = direction or INCOMING

        sockname = connection.socket.getsockname()
        if len(sockname) == 2:
            (self.remote_host,
             self.remote_host_port) = sockname
        elif len(sockname) == 1:
            self.remote_host = sockname[0]
            self.remote_host_port = 0
        else:
            self.remote_host = "0.0.0.0"
            self.remote_host_port = 0

        self.remote_host_port = int(self.remote_host_port)
        self.remote_process_name = None
        self.requested_version = PROTOCOL_VERSION

        # We need to use two separate message factories to avoid message ID
        # collision while assembling fragmented messages.
        self.request_message_factory = MessageFactory(self.remote_host,
                                                      self.remote_host_port)
        self.response_message_factory = MessageFactory(self.remote_host,
                                                       self.remote_host_port)

        # Queue of unprocessed incoming calls.
        self._messages = queues.Queue()

        # Map from message ID to futures for responses of outgoing calls.
        self._outbound_pending_call = {}

        # Total number of pending outbound requests and responses.
        self.total_outbound_pendings = 0

        # Collection of request IDs known to have timed out.
        self._request_tombstones = Cemetery()

        # Whether _loop is running. The loop doesn't run until after the
        # handshake has been performed.
        self._loop_running = False

        self.tchannel = tchannel
        self._close_cb = None
        # callback that will be called when there is a change in the outbound
        # pending request/response lists.
        self._outbound_pending_change_cb = None

        self.reader = Reader(self.connection)
        self.writer = Writer(self.connection)

        connection.set_close_callback(self._on_close)

    def set_outbound_pending_change_callback(self, cb):
        """Specify a function to be called when outbound pending request or
        response list changed.
        """
        self._outbound_pending_change_cb = cb

    def set_close_callback(self, cb):
        """Specify a function to be called when this connection is closed.

        :param cb:
            A callable that takes no arguments. This callable will be called
            when this connection is closed.
        """
        assert self._close_cb is None, (
            'A close_callback has already been set for this connection.'
        )
        self._close_cb = stack_context.wrap(cb)

    def _on_close(self):
        self.closed = True
        self._request_tombstones.clear()

        for message_id, future in self._outbound_pending_call.iteritems():
            future.set_exception(
                NetworkError(
                    "canceling outstanding request %d" % message_id
                )
            )
        self._outbound_pending_call = {}

        try:
            while True:
                message = self._messages.get_nowait()
                log.warn(
                    "Unconsumed message %s while closing connection %s",
                    message, self,
                )
        except queues.QueueEmpty:
            pass

        if self._close_cb:
            self._close_cb()

    def await(self):
        """Get the next call to this TChannel."""
        if self._loop_running:
            return self._messages.get()
        else:
            return self.reader.get()

    @tornado.gen.coroutine
    def _loop(self):
        # Receive messages off the wire. All messages are either responses to
        # outstanding requests or calls.
        #
        # Must be started only after the handshake has been performed.
        self._loop_running = True

        while not self.closed:
            try:
                message = yield self.reader.get()
            except StreamClosedError:
                break

            # TODO: There should probably be a try-catch on the yield.
            if message.message_type in self.CALL_REQ_TYPES:
                self._messages.put(message)
                continue

            elif message.id in self._outbound_pending_call:
                # set exception if receive error message
                if message.message_type == Types.ERROR:
                    future = self._outbound_pending_call.pop(message.id)
                    if future.running():
                        error = TChannelError.from_code(
                            message.code,
                            description=message.description,
                            id=message.id,
                            tracing=message.tracing,
                        )
                        future.set_exception(error)
                    else:
                        protocol_exception = (
                            self.response_message_factory.build(message)
                        )
                        if protocol_exception:
                            self.event_emitter.fire(
                                EventType.after_receive_error,
                                protocol_exception,
                            )
                    continue

                response = self.response_message_factory.build(message)

                # keep continue message in the list
                # pop all other type messages including error message
                if (message.message_type in self.CALL_RES_TYPES and
                        message.flags == FlagsType.fragment):
                    # still streaming, keep it for record
                    future = self._outbound_pending_call.get(message.id)
                else:
                    future = self._outbound_pending_call.pop(message.id)

                if response and future.running():
                    future.set_result(response)
                continue

            elif message.id in self._request_tombstones:
                # Recently timed out. Safe to ignore.
                continue

            log.info('Unconsumed message %s', message)

    # Basically, the only difference between send and write is that send
    # sets up a Future to get the response. That's ideal for peers making
    # calls. Peers responding to calls must use write.
    def send(self, message):
        """Send the given message up the wire.
        Use this for messages which have a response message.

        :param message:
            Message to send
        :returns:
            A Future containing the response for the message
        """
        assert self._loop_running, "Perform a handshake first."
        assert message.message_type in self.CALL_REQ_TYPES, (
            "Message '%s' can't use send" % repr(message)
        )

        message.id = message.id or self.writer.next_message_id()
        assert message.id not in self._outbound_pending_call, (
            "Message ID '%d' already being used" % message.id
        )

        future = tornado.gen.Future()
        self._outbound_pending_call[message.id] = future
        self.write(message)
        return future

    def write(self, message):
        """Writes the given message up the wire.

        Does not expect a response back for the message.

        :param message:
            Message to write.
        """
        message.id = message.id or self.writer.next_message_id()

        if message.message_type in self.CALL_REQ_TYPES:
            message_factory = self.request_message_factory
        else:
            message_factory = self.response_message_factory

        fragments = message_factory.fragment(message)
        return tornado.gen.multi(
            self.writer.put(fragment) for fragment in fragments
        )

    def close(self):
        if not self.closed:
            # TODO this is a temporary fix against "socket is None" error
            # that randomly happens in vcr-related tests.
            # https://github.com/uber/tchannel-python/issues/416
            try:
                self.connection.close()
            except:
                log.exception('Error when closing connection')
            self.closed = True

    @tornado.gen.coroutine
    def initiate_handshake(self, headers):
        """Initiate a handshake with the remote host.

        :param headers:
            A dictionary of headers to send.
        :returns:
            A future that resolves (with a value of None) when the handshake
            is complete.
        """
        self.writer.put(messages.InitRequestMessage(
            version=PROTOCOL_VERSION,
            headers=headers
        ))
        init_res = yield self.reader.get()
        if init_res.message_type != Types.INIT_RES:
            raise errors.InvalidMessageError(
                "Expected handshake response, got %s" % repr(init_res)
            )
        self._extract_handshake_headers(init_res)

        # The receive loop is started only after the handshake has been
        # completed.
        self._loop()

        raise tornado.gen.Return(init_res)

    @tornado.gen.coroutine
    def expect_handshake(self, headers):
        """Expect a handshake from the remote host.

        :param headers:
            Headers to respond with
        :returns:
            A future that resolves (with a value of None) when the handshake
            is complete.
        """
        init_req = yield self.reader.get()
        if init_req.message_type != Types.INIT_REQ:
            raise errors.InvalidMessageError(
                "You need to shake my hand first. Got %s" % repr(init_req)
            )
        self._extract_handshake_headers(init_req)

        self.writer.put(
            messages.InitResponseMessage(
                PROTOCOL_VERSION, headers, init_req.id),
        )

        # The receive loop is started only after the handshake has been
        # completed.
        self._loop()

        raise tornado.gen.Return(init_req)

    def _extract_handshake_headers(self, message):
        if not message.host_port:
            raise errors.InvalidMessageError(
                'Missing required header: host_port'
            )

        if not message.process_name:
            raise errors.InvalidMessageError(
                'Missing required header: process_name'
            )

        (self.remote_host,
         self.remote_host_port) = message.host_port.rsplit(':', 1)
        self.remote_host_port = int(self.remote_host_port)
        self.remote_process_name = message.process_name
        self.requested_version = message.version

    @classmethod
    @tornado.gen.coroutine
    def outgoing(cls, hostport, process_name=None, serve_hostport=None,
                 handler=None, tchannel=None):
        """Initiate a new connection to the given host.

        :param hostport:
            String in the form ``$host:$port`` specifying the target host
        :param process_name:
            Process name of the entity making the connection.
        :param serve_hostport:
            String in the form ``$host:$port`` specifying an address at which
            the caller can be reached. If omitted, ``0.0.0.0:0`` is used.
        :param handler:
            If given, any calls received from this connection will be sent to
            this RequestHandler.
        """
        host, port = hostport.rsplit(":", 1)
        process_name = process_name or "%s[%s]" % (sys.argv[0], os.getpid())
        serve_hostport = serve_hostport or "0.0.0.0:0"

        # TODO: change this to tornado.tcpclient.TCPClient to do async DNS
        # lookups.
        stream = tornado.iostream.IOStream(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        )

        log.debug("Connecting to %s", hostport)
        try:
            yield stream.connect((host, int(port)))

            connection = cls(stream, tchannel, direction=OUTGOING)

            log.debug("Performing handshake with %s", hostport)

            yield connection.initiate_handshake(headers={
                'host_port': serve_hostport,
                'process_name': process_name,
                'tchannel_language': TCHANNEL_LANGUAGE,
                'tchannel_language_version': TCHANNEL_LANGUAGE_VERSION,
                'tchannel_version': TCHANNEL_VERSION,
            })
        except (StreamClosedError, socket.error) as e:
            log.warn("Couldn't connect to %s", hostport)
            raise NetworkError(
                "Couldn't connect to %s" % hostport, e
            )

        if handler:
            connection.serve(handler)

        raise tornado.gen.Return(connection)

    @tornado.gen.coroutine
    def serve(self, handler):
        """Serve calls over this connection using the given RequestHandler.

        :param handler:
            RequestHandler to process the requests through
        :return:
            A Future that resolves (to None) once the loop is done running --
            which happens once this connection is closed.
        """
        assert handler, "handler is required"
        assert self._loop_running, "Finish the handshake first"

        while not self.closed:
            message = yield self.await()

            try:
                handler(message, self)
            except Exception:
                # TODO Send error frame back
                logging.exception("Failed to process %s", repr(message))

    def send_error(self, error):
        """Convenience method for writing Error frames up the wire.

        :param error:
            TChannel Error. :py:class`tchannel.errors.TChannelError`.
        :returns:
            A future that resolves when the write finishes.
        """

        error_message = build_raw_error_message(error)
        write_future = self.writer.put(error_message)
        write_future.add_done_callback(
            lambda f: self.tchannel.event_emitter.fire(
                EventType.after_send_error,
                error,
            )
        )
        return write_future

    def ping(self):
        return self.writer.put(messages.PingRequestMessage())

    def pong(self):
        return self.writer.put(messages.PingResponseMessage())

    def add_pending_outbound(self):
        self.total_outbound_pendings += 1
        if self._outbound_pending_change_cb:
            self._outbound_pending_change_cb()

    def remove_pending_outbound(self):
        self.total_outbound_pendings -= 1
        if self._outbound_pending_change_cb:
            self._outbound_pending_change_cb()


class StreamConnection(TornadoConnection):
    """Streaming request/response into protocol messages and sent by tornado
    connection

    Here are public apis provided by StreamConnection:
    "post_response(response)"
        stream response object into wire

    "stream_request(request)"
        stream request object into wire without waiting for a response

    "send_request(request)"
        stream request object into wire and wait for a response

    """

    @tornado.gen.coroutine
    def _stream(self, context, message_factory):
        """write request/response into frames

        Transform request/response into protocol level message objects based on
        types and argstreams.

        Assumption: the chunk data read from stream can fit into memory.

        If arg stream is at init or streaming state, build the message based on
        current chunk. If arg stream is at completed state, put current chunk
        into args[] array, and continue to read next arg stream in order to
        compose a larger message instead of sending multi small messages.

        Note: the message built at this stage is not guaranteed the size is
        less then 64KB.

        Possible messages created sequence:

        Take request as an example::
        CallRequestMessage(flags=fragment)
            --> CallRequestContinueMessage(flags=fragment)
            ....
            --> CallRequestContinueMessage(flags=fragment)
                --> CallRequestMessage(flags=none)

        :param context: Request or Response object
        """
        args = []
        try:
            for argstream in context.argstreams:
                chunk = yield argstream.read()
                args.append(chunk)
                chunk = yield argstream.read()
                while chunk:
                    message = (message_factory.
                               build_raw_message(context, args))
                    yield self.write(message)
                    args = [chunk]
                    chunk = yield argstream.read()

            # last piece of request/response.
            message = (message_factory.
                       build_raw_message(context, args, is_completed=True))
            yield self.write(message)
            context.state = StreamState.completed
        # Stop streamming immediately if exception occurs on the handler side
        except TChannelError:
            # raise by tchannel intentionally
            log.info("Stopped outgoing streams because of an error",
                     exc_info=sys.exc_info())

    @tornado.gen.coroutine
    def post_response(self, response):
        try:
            self.add_pending_outbound()
            # TODO: before_send_response
            yield self._stream(response, self.response_message_factory)

            # event: send_response
            self.tchannel.event_emitter.fire(
                EventType.after_send_response,
                response,
            )
        finally:
            self.remove_pending_outbound()
            response.close_argstreams(force=True)

    def stream_request(self, request, out_future):
        """send the given request and response is not required"""
        request.close_argstreams()

        def on_done(future):
            if future.exception() and out_future.running():
                out_future.set_exc_info(future.exc_info())
            request.close_argstreams(force=True)

        stream_future = self._stream(request, self.request_message_factory)
        stream_future.add_done_callback(on_done)
        return stream_future

    def send_request(self, request):
        """Send the given request and response is required.

        Use this for messages which have a response message.

        :param request:
            request to send
        :returns:
            A Future containing the response for the request
        """
        assert self._loop_running, "Perform a handshake first."

        assert request.id not in self._outbound_pending_call, (
            "Message ID '%d' already being used" % request.id
        )

        future = tornado.gen.Future()
        self._outbound_pending_call[request.id] = future
        self.add_pending_outbound()
        self.stream_request(request, future).add_done_callback(
            lambda f: self.remove_pending_outbound()
        )

        if request.ttl:
            self._add_timeout(request, future)

        # the actual future that caller will yield
        response_future = tornado.gen.Future()
        # TODO: fire before_receive_response

        IOLoop.current().add_future(
            future,
            lambda f: self.adapt_result(f, request, response_future),
        )
        return response_future

    def adapt_result(self, f, request, response_future):
        if not response_future.running():
            return

        if f.exception():
            cls, protocol_exception, tb = f.exc_info()
            protocol_exception.tracing = request.tracing
            response_future.set_exc_info((cls, protocol_exception, tb))

        else:
            response = f.result()
            response.tracing = request.tracing
            response_future.set_result(response)

    def remove_outstanding_request(self, request):
        """Remove request from pending request list"""
        self._outbound_pending_call.pop(request.id, None)

    def _add_timeout(self, request, future):
        """Adds a timeout for the given request to the given future."""
        io_loop = IOLoop.current()
        t = io_loop.call_later(
            request.ttl,
            self._request_timed_out, request.id, request.ttl, future,
        )
        io_loop.add_future(future, lambda f: io_loop.remove_timeout(t))
        # If the future finished before the timeout, we want the IOLoop to
        # forget about it, especially because we want to avoid memory
        # leaks with very large timeouts.

    def _request_timed_out(self, req_id, req_ttl, future):
        if not future.running():  # Already done.
            return

        # Fail the ongoing request and leave a tombstone behind for a short
        # while.
        future.set_exception(errors.TimeoutError())
        self._request_tombstones.add(req_id, req_ttl)


class Reader(object):

    def __init__(self, io_stream, capacity=None):
        capacity = capacity or 64

        self.queue = queues.Queue()
        self.filling = False
        self.io_stream = io_stream

    def fill(self):
        self.filling = True

        io_loop = IOLoop.current()

        def keep_reading(f):
            put_future = self.queue.put(f)

            if f.exception():
                self.filling = False
                if isinstance(f.exception(), StreamClosedError):
                    return log.info("read error", exc_info=f.exc_info())
                else:
                    return log.error("read error", exc_info=f.exc_info())

            # connect these two in the case when put blocks
            put_future.add_done_callback(
                lambda f: io_loop.spawn_callback(self.fill),
            )

        read_message(self.io_stream).add_done_callback(keep_reading)

    def get(self):
        """Receive the next message off the wire.

        :returns:
            A Future that resolves to the next message off the wire.
        """
        if not self.filling:
            self.fill()

        answer = tornado.gen.Future()

        def _on_result(future):
            if future.exception():
                return answer.set_exc_info(future.exc_info())
            answer.set_result(future.result())

        def _on_item(future):
            if future.exception():
                return answer.set_exc_info(future.exc_info())
            future.result().add_done_callback(_on_result)

        self.queue.get().add_done_callback(_on_item)
        return answer


class Writer(object):

    def __init__(self, io_stream, capacity=None):
        capacity = capacity or 64

        self.queue = queues.Queue()
        self.draining = False
        self.io_stream = io_stream
        # Tracks message IDs for this connection.
        self._id_sequence = 0

    def drain(self):
        self.draining = True

        io_loop = IOLoop.current()

        def on_write(f, done):
            if f.exception():
                log.error("write failed", exc_info=f.exc_info())
                done.set_exc_info(f.exc_info())
            else:
                done.set_result(f.result())

            io_loop.spawn_callback(next_write)

        def on_message(f):
            if f.exception():
                io_loop.spawn_callback(next_write)
                log.error("queue get failed", exc_info=f.exc_info())
                return

            message, done = f.result()
            try:
                # write() may raise if the stream was closed while we were
                # waiting for an entry in the queue.
                write_future = self.io_stream.write(message)
            except Exception:
                io_loop.spawn_callback(next_write)
                done.set_exc_info(sys.exc_info())
            else:
                io_loop.add_future(write_future, lambda f: on_write(f, done))

        def next_write():
            if self.io_stream.closed():
                return

            io_loop.add_future(self.queue.get(), on_message)

        io_loop.spawn_callback(next_write)

    def put(self, message):
        """Enqueues the given message for writing to the wire.

        The message must be small enough to fit in a single frame.
        """
        if self.draining is False:
            self.drain()

        return self._enqueue(message)

    def next_message_id(self):
        self._id_sequence = (self._id_sequence + 1) % MAX_MESSAGE_ID
        return self._id_sequence

    def _enqueue(self, message):
        message.id = message.id or self.next_message_id()
        done_writing_future = tornado.gen.Future()

        try:
            payload = messages.RW[message.message_type].write(
                message, BytesIO()
            ).getvalue()
        except Exception:
            done_writing_future.set_exc_info(sys.exc_info())
            return done_writing_future

        f = frame.Frame(
            header=frame.FrameHeader(
                message_type=message.message_type,
                message_id=message.id,
            ),
            payload=payload
        )

        try:
            body = frame.frame_rw.write(f, BytesIO()).getvalue()
        except Exception:
            done_writing_future.set_exc_info(sys.exc_info())
            return done_writing_future

        def on_queue_error(f):
            if f.exception():
                done_writing_future.set_exc_info(f.exc_info())

        self.queue.put(
            (body, done_writing_future)
        ).add_done_callback(on_queue_error)
        return done_writing_future

##############################################################################


FRAME_SIZE_WIDTH = frame.frame_rw.size_rw.width()


def read_message(stream):
    """Reads a message from the given IOStream.

    :param IOStream stream:
        IOStream to read from.
    """
    answer = tornado.gen.Future()
    io_loop = IOLoop.current()

    def on_error(future):
        log.info('Failed to read data: %s', future.exception())
        return answer.set_exc_info(future.exc_info())

    @fail_to(answer)
    def on_body(size, future):
        if future.exception():
            return on_error(future)

        body = future.result()
        f = frame.frame_rw.read(BytesIO(body), size=size)
        message_type = f.header.message_type
        message_rw = messages.RW.get(message_type)
        if not message_rw:
            exc = errors.FatalProtocolError(
                'Unknown message type %s', str(message_type)
            )
            return answer.set_exception(exc)

        message = message_rw.read(BytesIO(f.payload))
        message.id = f.header.message_id
        answer.set_result(message)

    @fail_to(answer)
    def on_read_size(future):
        if future.exception():
            return answer.set_exc_info(future.exc_info())

        size_bytes = future.result()
        size = frame.frame_rw.size_rw.read(BytesIO(size_bytes))
        io_loop.add_future(
            stream.read_bytes(size - FRAME_SIZE_WIDTH),
            lambda f: on_body(size, f)
        )

    try:
        # read_bytes may fail if the stream has already been closed
        read_size_future = stream.read_bytes(FRAME_SIZE_WIDTH)
    except Exception:
        answer.set_exc_info(sys.exc_info())
    else:
        read_size_future.add_done_callback(on_read_size)
    return answer
