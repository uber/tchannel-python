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

from ..errors import FatalProtocolError
from ..errors import InvalidChecksumError
from ..errors import TChannelError
from ..messages import RW
from ..messages import Types
from ..messages import common
from ..messages.call_continue import CallContinueMessage
from ..messages.call_request import CallRequestMessage
from ..messages.call_request_continue import CallRequestContinueMessage
from ..messages.call_response import CallResponseMessage
from ..messages.call_response_continue import CallResponseContinueMessage
from ..messages.common import FlagsType
from ..messages.common import StreamState
from ..messages.common import Tracing
from ..messages.common import generate_checksum
from ..messages.common import verify_checksum
from ..messages.error import ErrorMessage
from ..zipkin.annotation import Endpoint
from ..zipkin.trace import Trace
from .request import Request
from .response import Response
from .stream import InMemStream

log = logging.getLogger('tchannel')


def build_raw_error_message(protocol_exception):
    """build protocol level error message based on Error object"""
    message = ErrorMessage(
        code=protocol_exception.code,
        tracing=Tracing(
            protocol_exception.tracing.span_id,
            protocol_exception.tracing.parent_span_id,
            protocol_exception.tracing.trace_id,
            protocol_exception.tracing.traceflags),
        description=protocol_exception.description,
    )

    return message


def build_raw_request_message(request, args, is_completed=False):
    """build protocol level message based on request and args.

    request object contains meta information about outgoing request.
    args are the currently chunk data from argstreams
    is_completed tells the flags of the message

    :param request: Request
    :param args: array of arg streams
    :param is_completed: flag to tell whether the request is completed or not
    :return: CallRequestMessage/CallRequestContinueMessage
    """
    request.flags = FlagsType.none if is_completed else FlagsType.fragment

    # TODO decide what need to pass from request
    if request.state == StreamState.init:
        message = CallRequestMessage(
            id=request.id,
            flags=request.flags,
            ttl=request.ttl * 1000,
            tracing=Tracing(request.tracing.span_id,
                            request.tracing.parent_span_id,
                            request.tracing.trace_id,
                            request.tracing.traceflags),
            service=request.service,
            headers=request.headers,
            checksum=request.checksum,
            args=args,
        )
        request.state = (StreamState.completed if is_completed
                         else StreamState.streaming)
    elif request.state == StreamState.streaming:
        message = CallRequestContinueMessage(
            id=request.id,
            flags=request.flags,
            checksum=request.checksum,
            args=args,
        )
        request.state = (StreamState.completed if is_completed
                         else StreamState.streaming)

    message.id = request.id
    return message


def build_raw_response_message(response, args, is_completed=False):
    """build protocol level message based on response and args.

    response object contains meta information about outgoing response.
    args are the currently chunk data from argstreams
    is_completed tells the flags of the message

    :param response: Response
    :param args: array of arg streams
    :param is_completed: flag to tell whether the request is completed or not
    :return: CallResponseMessage/CallResponseContinueMessage
    """
    response.flags = FlagsType.none if is_completed else FlagsType.fragment

    # TODO decide what need to pass from request
    if response.state == StreamState.init:
        message = CallResponseMessage(
            id=response.id,
            flags=response.flags,
            code=response.code,
            tracing=Tracing(response.tracing.span_id,
                            response.tracing.parent_span_id,
                            response.tracing.trace_id,
                            response.tracing.traceflags),
            headers=response.headers,
            checksum=response.checksum,
            args=args,
        )
        response.state = (StreamState.completed if is_completed
                          else StreamState.streaming)
    elif response.state == StreamState.streaming:
        message = CallResponseContinueMessage(
            id=response.id,
            flags=response.flags,
            checksum=response.checksum,
            args=args,
        )
        response.state = (StreamState.completed if is_completed
                          else StreamState.streaming)

    message.id = response.id
    return message


def build_raw_message(reqres, args, is_completed=False):
    if isinstance(reqres, Request):
        return build_raw_request_message(reqres, args, is_completed)
    elif isinstance(reqres, Response):
        return build_raw_response_message(reqres, args, is_completed)


def prepare_args(message):
    args = [
        InMemStream(auto_close=False),
        InMemStream(auto_close=False),
        InMemStream(auto_close=False),
    ]
    for i, arg in enumerate(message.args):
        if i > 0:
            args[i - 1].close()
        args[i].write(arg)

    return args


def build_request(message, remote_host=None, remote_host_port=None):
    """Build request object from protocol level message info

    It is allowed to take incomplete CallRequestMessage. Therefore the
    created request may not contain whole three arguments.

    :param message: CallRequestMessage
    :param remote_host: remote host IP
    :param remote_host_port: remote host port
    :return: request object
    """

    args = prepare_args(message)

    tracing = Trace(
        trace_id=message.tracing.trace_id,
        span_id=message.tracing.span_id,
        parent_span_id=message.tracing.parent_id,
        endpoint=Endpoint(remote_host,
                          remote_host_port,
                          message.service),
        traceflags=message.tracing.traceflags
    )

    # TODO decide what to pass to Request from message
    req = Request(
        flags=message.flags,
        ttl=message.ttl / 1000.0,
        tracing=tracing,
        service=message.service,
        headers=message.headers,
        checksum=message.checksum,
        argstreams=args,
        id=message.id,
    )
    return req


def build_response(message):
    """Build response object from protocol level message info

    It is allowed to take incomplete CallResponseMessage. Therefore the
    created request may not contain whole three arguments.

    :param message: CallResponseMessage
    :return: response object
    """

    args = prepare_args(message)

    # TODO decide what to pass to Response from message
    res = Response(
        flags=message.flags,
        code=message.code,
        headers=message.headers,
        checksum=message.checksum,
        argstreams=args,
        id=message.id,
    )
    return res


def build_inbound_response(message):
    """Build new response based on incoming call response message.

    :param message:
        Incoming call response message message.
    :return:
        New response object.
    """
    if message.message_type != Types.CALL_RES:
        raise FatalProtocolError(
            "Receiving unexpected message type %d for message ID %d" %
            (message.message_type, message.id)
        )

    if not verify_checksum(message, 0):
        raise InvalidChecksumError("Checksum does not match!")
    response = build_response(message)
    num = _find_incomplete_stream(response)
    close_argstream(response, num)
    return response


def build_inbound_response_cont(message, response):
    """Add incoming call response continue message's data into
    corresponding pending response object.

    :param message:
        Incoming call response continue message.
    :param response:
        Corresponding pending response with same message Id.
    """
    if message.message_type != Types.CALL_RES_CONTINUE:
        raise FatalProtocolError(
            "Receiving unexpected message type %d for message ID %d" %
            (message.message_type, message.id)
        )

    if response is None:
        # missing call msg before continue msg
        raise FatalProtocolError(
            ("Received call response continuation for" +
             "unknown message %d" % message.id)
        )

    dst = _find_incomplete_stream(response)
    if not verify_checksum(message, response.checksum[1]):
        e = InvalidChecksumError("Checksum does not match!")
        response.argstreams[dst].set_exception(e)
        raise e
    else:
        response.checksum = message.checksum

    src = 0
    while src < len(message.args):
        response.argstreams[dst].write(message.args[src])
        dst += 1
        src += 1

    if message.flags != FlagsType.fragment:
        # get last fragment. mark it as completed
        assert (len(response.argstreams) ==
                CallContinueMessage.max_args_num)
        response.flags = FlagsType.none

    close_argstream(response, dst - 1)


def build_inbound_error(message):
    """convert error message to TChannelError type."""
    return TChannelError.from_code(
        message.code,
        description=message.description,
        tracing=message.tracing
    )


def build_inbound_request(message, remote_host=None, remote_host_port=None):
    """Build inbound request based on incoming call request message.

    :param message:
        Incoming call request message.
    :param remote_host: remote host IP
    :param remote_host_port: remote host port
    :return:
        New request object.
    """
    if message.message_type != Types.CALL_REQ:
        raise FatalProtocolError(
            "Receiving unexpected message type %d for message ID %d" %
            (message.message_type, message.id)
        )

    if not verify_checksum(message, 0):
        raise InvalidChecksumError("Checksum does not match!")
    request = build_request(message, remote_host, remote_host_port)
    num = _find_incomplete_stream(request)
    close_argstream(request, num)
    return request


def build_inbound_request_cont(message, request):
    """Add incoming call request continue message's data into
    corresponding pending request object.

    :param message:
        Incoming call request continue message.
    :param request:
        Corresponding pending response with same message Id.
    """
    if message.message_type != Types.CALL_REQ_CONTINUE:
        raise FatalProtocolError(
            "Receiving unexpected message type %d for message ID %d" %
            (message.message_type, message.id)
        )

    if request is None:
        # missing call msg before continue msg
        raise FatalProtocolError(
            "missing call message after receiving continue message"
        )

    dst = _find_incomplete_stream(request)
    if not verify_checksum(message, request.checksum[1]):
        e = InvalidChecksumError("Checksum does not match!")
        request.argstreams[dst].set_exception(e)
        raise e
    else:
        request.checksum = message.checksum

    src = 0
    while src < len(message.args):
        request.argstreams[dst].write(message.args[src])
        dst += 1
        src += 1

    if message.flags != FlagsType.fragment:
        # get last fragment. mark it as completed
        assert (len(request.argstreams) ==
                CallContinueMessage.max_args_num)
        request.flags = FlagsType.none

    close_argstream(request, dst - 1)


def _find_incomplete_stream(reqres):
    # find the incomplete stream
    num = 0
    for i, arg in enumerate(reqres.argstreams):
        if arg.state != StreamState.completed:
            num = i
            break
    return num


def fragment(message, reqres):
    """Fragment message based on max payload size

    note: if the message doesn't need to fragment,
    it will return a list which only contains original
    message itself.

    :param message: raw message
    :param reqres: request or response object
    :return: list of messages whose sizes <= max
        payload size
    """
    if message.message_type in [Types.CALL_RES,
                                Types.CALL_REQ,
                                Types.CALL_REQ_CONTINUE,
                                Types.CALL_RES_CONTINUE]:
        rw = RW[message.message_type]
        payload_space = (common.MAX_PAYLOAD_SIZE -
                         rw.length_no_args(message))
        # split a call/request message into an array
        # with a call/request message and {0~n} continue
        # message
        fragment_msg = message.fragment(payload_space)
        generate_checksum(message, reqres.checksum[1])
        reqres.checksum = message.checksum

        yield message
        while fragment_msg is not None:
            message = fragment_msg
            rw = RW[message.message_type]
            payload_space = (common.MAX_PAYLOAD_SIZE -
                             rw.length_no_args(message))
            fragment_msg = message.fragment(payload_space)
            generate_checksum(message, reqres.checksum[1])
            reqres.checksum = message.checksum
            yield message
    else:
        yield message


def close_argstream(request, num):
    # close the stream for completed args since we have received all
    # the chunks
    if request.flags == FlagsType.none:
        num += 1

    for i in range(num):
        request.argstreams[i].close()
