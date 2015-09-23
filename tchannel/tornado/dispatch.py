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

from __future__ import absolute_import

import logging
from collections import namedtuple

import tornado
import tornado.gen
from tornado import gen

from tchannel import transport
from tchannel.request import Request
from tchannel.request import TransportHeaders
from tchannel.response import response_from_mixed
from ..context import request_context
from ..errors import BadRequestError, DeclinedError
from ..errors import TChannelError
from ..event import EventType
from ..messages import Types
from ..messages.error import ErrorCode
from ..serializer.raw import RawSerializer
from .response import Response as DeprecatedResponse

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
        Then it will trigger the async call_handle call.

        :param message: CallRequestMessage or CallRequestContinueMessage
        :param connection: tornado connection
        """
        try:
            new_req = connection.message_factory.build_inbound_request(
                message, connection.get_incoming_request(message.id)
            )
            # message_factory will create Request only when it receives
            # CallRequestMessage. It will return None, if it receives
            # CallRequestContinueMessage.
            if new_req:
                if connection.draining:
                    # decline request
                    raise DeclinedError(connection.draining.reason)

                # process the new request
                connection.add_incoming_request(new_req)
                self.handle_call(new_req, connection).add_done_callback(
                    lambda _: connection.remove_incoming_request(
                        new_req.id
                    )
                )
        except TChannelError as e:
            log.warn('Received a bad request.', exc_info=True)

            connection.send_error(
                e.code,
                e.message,
                message.id,
            )

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

        response = None
        tchannel = connection.tchannel

        # event: receive_request
        request.tracing.name = request.endpoint
        tchannel.event_emitter.fire(EventType.before_receive_request, request)

        handler = self.handlers.get(request.endpoint)

        if handler is None:
            handler = self.handlers[self.FALLBACK]

        requested_as = request.headers.get('as', None)
        expected_as = handler.req_serializer.name

        if request.endpoint in self.handlers and requested_as != expected_as:
            connection.send_error(
                ErrorCode.bad_request,
                "Your serialization was '%s' but the server expected '%s'" % (
                    requested_as,
                    expected_as,
                ),
                request.id,
            )
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
        connection.post_response(response)

        try:
            # New impl - the handler takes a request and returns a response
            if self._handler_returns_response:

                # convert deprecated req to new top-level req
                b = yield request.get_body()
                he = yield request.get_header()
                t = request.headers
                t = transport.to_kwargs(t)
                t = TransportHeaders(**t)
                new_req = Request(
                    body=b,
                    headers=he,
                    transport=t,
                    endpoint=request.endpoint,
                )

                # Not safe to have coroutine yields statement within
                # stack context.
                # The right way to do it is:
                # with request_context(..):
                #    future = f()
                # yield future

                with request_context(request.tracing):
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
                with request_context(request.tracing):
                    f = handler.endpoint(request, response)

                yield gen.maybe_future(f)

            response.flush()
        except TChannelError as e:
            response.set_exception(e)
            connection.send_error(e.code, e.message, request.id)
        except Exception as e:
            msg = "An unexpected error has occurred from the handler"
            log.exception(msg)

            response.set_exception(TChannelError(e.message))

            connection.send_error(ErrorCode.unexpected, msg, response.id)
            tchannel.event_emitter.fire(EventType.on_exception, request, e)

        raise gen.Return(response)

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
