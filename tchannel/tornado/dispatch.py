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

from collections import defaultdict
from collections import namedtuple

import tornado
import tornado.gen
from tornado import gen

from ..errors import InvalidEndpointError
from ..errors import TChannelError
from ..event import EventType
from ..messages.error import ErrorCode
from ..serializer.raw import RawSerializer
from .response import Response

from ..errors import InvalidChecksumError
from ..errors import StreamingError
from ..messages import Types


Handler = namedtuple('Handler', 'endpoint req_serializer resp_serializer')


class RequestDispatcher(object):
    """A synchronous RequestHandler that dispatches calls to different
    endpoints based on ``arg1``.

    Endpoints are registered using ``register`` or the ``route``
    decorator.

    .. code-block:: python

        handler = # ...

        @handler.route('my_method')
        def my_method(request, response, proxy):
            response.write('hello world')
    """

    FALLBACK = object()

    def __init__(self, _handler_returns_response=False):
        self.handlers = defaultdict(lambda: Handler(
            self.not_found, RawSerializer(), RawSerializer())
        )
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
            req = connection.request_message_factory.build(message)
            # message_factory will create Request only when it receives
            # CallRequestMessage. It will return None, if it receives
            # CallRequestContinueMessage.
            if req:
                self.handle_call(req, connection)

        except (InvalidChecksumError, StreamingError) as e:
            connection.send_error(
                ErrorCode.bad_request,
                e.message,
                message.id,
            )
        except Exception:
            connection.send_error(
                ErrorCode.unexpected,
                "An unexpected error has occurred.",
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
        response = None
        while chunk:
            request.endpoint += chunk
            chunk = yield request.argstreams[0].read()

        # event: receive_request
        request.tracing.name = request.endpoint

        connection.tchannel.event_emitter.fire(
            EventType.before_receive_request,
            request,
        )

        handler = self.handlers[request.endpoint]
        if request.headers.get('as', None) != handler.req_serializer.name:
            connection.send_error(
                ErrorCode.bad_request,
                "Invalid arg scheme in request header",
                request.id,
            )
            raise gen.Return(None)

        request.serializer = handler.req_serializer
        response = Response(
            id=request.id,
            checksum=request.checksum,
            tracing=request.tracing,
            connection=connection,
            headers={'as': request.headers.get('as', 'raw')},
            serializer=handler.resp_serializer,
        )

        connection.post_response(response)

        import ipdb
        ipdb.set_trace()

        try:

            # New impl - the handler takes a request and returns a response
            if self._handler_returns_response:

                # convert deprecated req to new top-level req

                # get new top-level resp from controller
                new_resp = yield gen.maybe_future(
                    handler.endpoint(request)
                )
                print(new_resp)

                # assign resp values to dep response
                import ipdb
                ipdb.set_trace()

            # Dep impl - the handler is provided with a req & resp writer
            else:
                yield gen.maybe_future(
                    handler.endpoint(
                        request,
                        response,
                        TChannelProxy(
                            connection.tchannel,
                            request.tracing,
                        ),
                    )
                )

            response.flush()
        except InvalidEndpointError as e:
            connection.send_error(
                ErrorCode.bad_request,
                e.message,
                request.id,
            )
        except Exception as e:
            response.set_exception(TChannelError(e.message))
            connection.request_message_factory.remove_buffer(response.id)
            connection.send_error(
                ErrorCode.unexpected,
                "An unexpected error has occurred from the handler",
                response.id,
            )
            connection.tchannel.event_emitter.fire(
                EventType.on_exception,
                request,
                e,
            )

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
            def check_health(request, response, proxy):
                # ...

        :param rule:
            Name of the endpoint. Incoming Call Requests must have this as
            ``arg1`` to dispatch to this handler.

            If ``RequestHandler.FALLBACK`` is specified as a rule, the given
            handler will be used as the 'fallback' handler when requests don't
            match any registered rules.

        :param handler:
            A function that gets called with ``Request``, ``Response``, and
            the ``proxy``.

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
        if rule is self.FALLBACK:
            self.handlers.default_factory = lambda: Handler(
                handler, RawSerializer(), RawSerializer()
            )
            return

        self.handlers[rule] = Handler(handler, req_serializer, resp_serializer)

    @staticmethod
    def not_found(request, response, proxy):
        """Default behavior for requests to unrecognized endpoints."""
        raise InvalidEndpointError(
            "Endpoint '%s' for service '%s' is not defined" % (
                request.endpoint,
                request.service,
            ),
        )


class TChannelProxy(object):
    """TChannel Proxy with additional runtime info

    TChannelProxy contains parent_tracing information which is created by
    received request.

    TChannelProxy will be used as one parameter for the request handler.

    Example::

        def handler(request, response, proxy):

    """
    __slots__ = ('_tchannel', 'parent_tracing')

    def __init__(self, tchannel, parent_tracing=None):
        self._tchannel = tchannel
        self.parent_tracing = parent_tracing

    @property
    def closed(self):
        return self._tchannel.closed

    @property
    def hostport(self):
        return self._tchannel.hostport

    def request(self, hostport=None, service=None, **kwargs):
        kwargs['parent_tracing'] = self.parent_tracing
        return self._tchannel.request(hostport,
                                      service,
                                      **kwargs)
