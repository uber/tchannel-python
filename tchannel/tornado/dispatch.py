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
import sys
from collections import namedtuple

import tornado
import tornado.gen
from tornado import gen
from tornado.iostream import StreamClosedError

from tchannel.request import Request
from tchannel.request import TransportHeaders
from tchannel.response import response_from_mixed
from ..errors import BadRequestError
from ..errors import UnexpectedError
from ..errors import TChannelError
from ..event import EventType
from ..messages import Types
from ..serializer.raw import RawSerializer
from .response import Response as DeprecatedResponse
from .. import tracing

log = logging.getLogger('tchannel')


Handler = namedtuple('Handler', 'endpoint req_serializer resp_serializer')


class RequestDispatcher(object):
    """A synchronous RequestHandler that dispatches calls to different
    endpoints based on ``arg1``.

    Endpoints are registered using ``register`` or the ``route``
    decorator.

    .. code-block:: python

        handler = # ...

        @handler.route('my_method')
        def my_method(request, response):
            response.write('hello world')
    """

    FALLBACK = object()

    def __init__(self, _handler_returns_response=False):
        self.handlers = {}
        self.register(self.FALLBACK, self.not_found)
        self._handler_returns_response = _handler_returns_response

    _HANDLER_NAMES = {
        Types.CALL_REQ: 'pre_call',
        Types.CALL_REQ_CONTINUE: 'pre_call'
    }

    def handle(self, message, connection):
        # TODO assert that the handshake was already completed
        assert message, "message must not be None"

        if message.message_type not in self._HANDLER_NAMES:
            # TODO handle this more gracefully
            raise NotImplementedError("Unexpected message: %s" % str(message))

        handler_name = "handle_" + self._HANDLER_NAMES[message.message_type]
        return getattr(self, handler_name)(message, connection)

    def handle_pre_call(self, message, connection):
        """Handle incoming request message including CallRequestMessage and
        CallRequestContinueMessage

        This method will build the User friendly request object based on the
        incoming messages.

        It passes all the messages into the message_factory to build the init
        request object. Only when it get a CallRequestMessage and a completed
        arg_1=argstream[0], the message_factory will return a request object.
        Then it will trigger the async handle_call method.

        :param message: CallRequestMessage or CallRequestContinueMessage
        :param connection: tornado connection
        """
        req = None
        try:
            req = connection.request_message_factory.build(message)
            # message_factory will create Request only when it receives
            # CallRequestMessage. It will return None, if it receives
            # CallRequestContinueMessage.
            if req:
                self.handle_call(req, connection)

        except TChannelError as e:
            log.warn('Received a bad request.', exc_info=True)
            if req:
                e.tracing = req.tracing
            connection.send_error(e)

    @tornado.gen.coroutine
    def handle_call(self, request, connection):
        # read arg_1 so that handle_call is able to get the endpoint
        # name and find the endpoint handler.
        # the arg_1 value will be store in the request.endpoint field.

        # NOTE: after here, the correct way to access value of arg_1 is through
        # request.endpoint. The original argstream[0] is no longer valid. If
        # user still tries read from it, it will return empty.
        chunk = yield request.argstreams[0].read()
        while chunk:
            request.endpoint += chunk
            chunk = yield request.argstreams[0].read()

        log.debug('Received a call to %s.', request.endpoint)

        tchannel = connection.tchannel

        tchannel.event_emitter.fire(EventType.before_receive_request, request)

        handler = self.get_endpoint(request.endpoint)

        requested_as = request.headers.get('as', None)
        expected_as = handler.req_serializer.name

        if request.endpoint in self.handlers and requested_as != expected_as:
            connection.send_error(BadRequestError(
                description=(
                    "Server expected a '%s' but request is '%s'"
                    % (
                        expected_as,
                        requested_as,
                    )
                ),
                id=request.id,
                tracing=request.tracing,
            ))

            raise gen.Return(None)

        request.serializer = handler.req_serializer
        response = DeprecatedResponse(
            id=request.id,
            checksum=request.checksum,
            tracing=request.tracing,
            connection=connection,
            headers={'as': request.headers.get('as', 'raw')},
            serializer=handler.resp_serializer,
        )

        def _on_post_response(future):
            if not future.exception():
                return

            # Failed to write response because client disappeared. Nothing to
            # do.
            if isinstance(future.exception(), StreamClosedError):
                return

            log.error('failed to write response', exc_info=future.exc_info())

        connection.post_response(response).add_done_callback(_on_post_response)

        tracer = tracing.ServerTracer(
            tracer=tchannel.tracer, operation_name=request.endpoint
        )
        tracer.start_basic_span(request)

        try:
            # New impl - the handler takes a request and returns a response
            if self._handler_returns_response:
                # convert deprecated req to new top-level req
                b = yield request.get_body()
                he = yield request.get_header()
                t = TransportHeaders.from_dict(request.headers)
                new_req = Request(
                    body=b,
                    headers=he,
                    transport=t,
                    endpoint=request.endpoint,
                    service=request.service,
                    timeout=request.ttl,
                )
                with tracer.start_span(
                    request=request, headers=he,
                    peer_host=connection.remote_host,
                    peer_port=connection.remote_host_port
                ) as span:
                    context_provider = tchannel.context_provider_fn()
                    with context_provider.span_in_context(span):
                        # Cannot yield while inside the StackContext
                        f = handler.endpoint(new_req)
                    new_resp = yield gen.maybe_future(f)

                # instantiate a tchannel.Response
                new_resp = response_from_mixed(new_resp)

                response.code = new_resp.status

                # assign resp values to dep response
                response.write_header(new_resp.headers)

                if new_resp.body is not None:
                    response.write_body(new_resp.body)

            # Dep impl - the handler is provided with a req & resp writer
            else:
                with tracer.start_span(
                    request=request, headers={},
                    peer_host=connection.remote_host,
                    peer_port=connection.remote_host_port
                ) as span:
                    context_provider = tchannel.context_provider_fn()
                    with context_provider.span_in_context(span):
                        # Cannot yield while inside the StackContext
                        f = handler.endpoint(request, response)

                    yield gen.maybe_future(f)

            response.flush()
        except TChannelError as e:
            e.tracing = request.tracing
            e.id = request.id
            connection.send_error(e)
        except Exception as e:
            # Maintain a reference to our original exc info because we stomp
            # the traceback below.
            exc_info = sys.exc_info()
            exc_type, exc_obj, exc_tb = exc_info
            try:
                # Walk to the traceback to find our offending line.
                while exc_tb.tb_next is not None:
                    exc_tb = exc_tb.tb_next

                description = "%r from %s in %s:%s" % (
                    e,
                    request.endpoint,
                    exc_tb.tb_frame.f_code.co_filename,
                    exc_tb.tb_lineno,
                )
                error = UnexpectedError(
                    description=description,
                    id=request.id,
                    tracing=request.tracing,
                )

                response.set_exception(error, exc_info=exc_info)
                connection.request_message_factory.remove_buffer(response.id)

                connection.send_error(error)
                tchannel.event_emitter.fire(
                    EventType.on_exception,
                    request,
                    error,
                )
                log.error("Unexpected error", exc_info=exc_info)
            finally:
                # Clean up circular reference.
                # https://docs.python.org/2/library/sys.html#sys.exc_info
                del exc_tb
                del exc_info
        raise gen.Return(response)

    def get_endpoint(self, name):
        handler = self.handlers.get(name)

        if handler is None:
            handler = self.handlers[self.FALLBACK]

        return handler

    def register(
            self,
            rule,
            handler,
            req_serializer=None,
            resp_serializer=None
    ):
        """Register a new endpoint with the given name.

        .. code-block:: python

            @dispatcher.register('is_healthy')
            def check_health(request, response):
                # ...

        :param rule:
            Name of the endpoint. Incoming Call Requests must have this as
            ``arg1`` to dispatch to this handler.

            If ``RequestHandler.FALLBACK`` is specified as a rule, the given
            handler will be used as the 'fallback' handler when requests don't
            match any registered rules.

        :param handler:
            A function that gets called with ``Request`` and ``Response``.

        :param req_serializer:
            Arg scheme serializer of this endpoint. It should be
            ``RawSerializer``, ``JsonSerializer``, and ``ThriftSerializer``.

        :param resp_serializer:
            Arg scheme serializer of this endpoint. It should be
            ``RawSerializer``, ``JsonSerializer``, and ``ThriftSerializer``.
        """

        assert handler, "handler must not be None"
        req_serializer = req_serializer or RawSerializer()
        resp_serializer = resp_serializer or RawSerializer()
        self.handlers[rule] = Handler(handler, req_serializer, resp_serializer)

    @staticmethod
    def not_found(request, response=None):
        """Default behavior for requests to unrecognized endpoints."""
        raise BadRequestError(
            description="Endpoint '%s' is not defined" % (
                request.endpoint,
            ),
        )
