import collections
from .messages import CallResponseMessage
from .messages import PingRequestMessage
from .messages import PingResponseMessage
from .messages.error import ErrorCode

Endpoint = collections.namedtuple('Endpoint', ['handler', 'opts'])


class RequestHandler(object):
    """Base class for request handlers.

    Usage example:
        class CustomerReqHandler(RequestHandler):
            def handle_request(self, context, conn):
                Add customized request handling
                logic here

    """
    def handle_request(self, context, conn):
        """Handle incoming request

        :param context: context contains received CallRequestMessage
        :param conn: An incoming TornadoConnection
        """
        raise NotImplementedError()


class TChannelRequestHandler(RequestHandler):
    def __init__(self):
        super(TChannelRequestHandler, self).__init__()
        self.endpoints = {}

    def handle_request(self, context, conn):
        """dispatch incoming request to particular endpoint

        :param context: context contains received CallRequestMessage
        :param conn: An incoming TornadoConnection
        """
        # TODO: stop passing conn around everywhere
        request = TChannelRequest(context, conn)
        endpoint = self._find_endpoint(request.method)
        if endpoint is not None:
            response = TChannelResponse(request, conn)
            try:
                endpoint.handler(request, response, endpoint.opts)
            # TODO add tchannel error handling here
            finally:
                response.finish()

        elif context.message.message_type == PingRequestMessage.message_type:
            response = TChannelResponse(request, conn)
            response.resp_msg = PingResponseMessage()
            response.finish()

        else:
            msg = "no such endpoint service={0} endpoint={1}".format(
                context.message.service, context.message.arg_1)
            conn.send_error(ErrorCode.bad_request, msg, context.message_id)

    def route(self, rule, **opts):
        def decorator(handler):
            self.register_handler(rule, handler, **opts)
            return handler

        return decorator

    def register_handler(self, rule, handler, **opts):
        self.endpoints[rule] = Endpoint(handler=handler, opts=opts)

    def _find_endpoint(self, rule):
        return self.endpoints.get(rule, None)


class TChannelRequest(object):
    """TChannel Request Wrapper"""

    __slots__ = ('message', 'header',
                 'body', 'method',
                 'connection', 'context',
                 'id')

    def __init__(self, context, conn):
        self.message = context.message
        self.header = getattr(self.message, 'arg_2', None)
        self.body = getattr(self.message, 'arg_3', None)
        self.method = getattr(self.message, 'arg_1', None)
        self.connection = conn
        self.context = context
        self.id = context.message_id

        # TODO fill up more attributes


class TChannelResponse(object):
    """TChannel Response Wrapper"""

    __slots__ = ('_connection', '_request',
                 'resp_msg', 'id')

    def __init__(self, request, conn):
        self._connection = conn
        self._request = request
        self.resp_msg = CallResponseMessage()
        self.id = request.id

    def write(self, chunk):
        # build response message
        self.resp_msg.arg_3 += chunk

    def finish(self):
        self._connection.finish(self)
        self.resp_msg = CallResponseMessage()

    def update_resp_id(self):
        self.id += 1
