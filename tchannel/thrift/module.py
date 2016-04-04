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

import inspect
import types

from tchannel.deprecate import deprecated
from tchannel.errors import ValueExpectedError
from tchannel.errors import OneWayNotSupportedError
from tchannel.serializer.thrift import ThriftSerializer

from .reflection import get_service_methods, get_module_name


@deprecated(
    "thrift_request_builder is deprecated and will be removed in 0.19.0. "
    "please switch usage to tchannel.thrift.load."
)
def thrift_request_builder(service, thrift_module, hostport=None,
                           thrift_class_name=None):
    """Provide TChannel compatibility with Thrift-generated modules.

    The service this creates is meant to be used with TChannel like so:

    .. code-block:: python

        from tchannel import TChannel, thrift_request_builder
        from some_other_service_thrift import some_other_service

        tchannel = TChannel('my-service')

        some_service = thrift_request_builder(
            service='some-other-service',
            thrift_module=some_other_service
        )

        resp = tchannel.thrift(
            some_service.fetchPotatoes()
        )

    .. deprecated:: 0.18.0

        Please switch to :py:func:`tchannel.thrift.load`.

    .. warning::

        This API is deprecated and will be removed in a future version.

    :param string service:
        Name of Thrift service to call. This is used internally for
        grouping and stats, but also to route requests over Hyperbahn.

    :param thrift_module:
        The top-level module of the Apache Thrift generated code for
        the service that will be called.

    :param string hostport:
        When calling the Thrift service directly, and not over Hyperbahn,
        this 'host:port' value should be provided.

    :param string thrift_class_name:
        When the Apache Thrift generated Iface class name does not match
        thrift_module, then this should be provided.
    """

    # start with a request maker instance
    maker = ThriftRequestMaker(
        service=service,
        thrift_module=thrift_module,
        hostport=hostport,
        thrift_class_name=thrift_class_name
    )

    # create methods that mirror thrift client
    # and each return ThriftRequest
    methods = _create_methods(thrift_module)

    # then attach to instane
    for name, method in methods.iteritems():
        method = types.MethodType(method, maker, ThriftRequestMaker)
        setattr(maker, name, method)

    return maker


class ThriftRequestMaker(object):

    def __init__(self, service, thrift_module,
                 hostport=None, thrift_class_name=None):

        self.service = service
        self.thrift_module = thrift_module
        self.hostport = hostport

        if thrift_class_name is not None:
            self.thrift_class_name = thrift_class_name
        else:
            self.thrift_class_name = get_module_name(self.thrift_module)

    def _make_request(self, method_name, args, kwargs):

        result_type = self._get_result_type(method_name)

        if result_type is None:
            raise OneWayNotSupportedError(
                'TChannel+Thrift does not currently support oneway '
                'procedures.'
            )

        endpoint = self._get_endpoint(method_name)
        call_args = self._get_call_args(method_name, args, kwargs)

        request = ThriftRequest(
            service=self.service,
            endpoint=endpoint,
            result_type=result_type,
            call_args=call_args,
            hostport=self.hostport
        )

        return request

    def _get_endpoint(self, method_name):

        endpoint = '%s::%s' % (self.thrift_class_name, method_name)

        return endpoint

    def _get_args_type(self, method_name):

        args_type = getattr(self.thrift_module, method_name + '_args')

        return args_type

    def _get_result_type(self, method_name):

        # if None then result_type is oneway
        result_type = getattr(
            self.thrift_module, method_name + '_result', None
        )

        return result_type

    def _get_call_args(self, method_name, args, kwargs):

        args_type = self._get_args_type(method_name)

        params = inspect.getcallargs(
            getattr(self.thrift_module.Iface, method_name),
            self,
            *args,
            **kwargs
        )
        params.pop('self')  # self is already known

        call_args = args_type()
        for name, value in params.items():
            setattr(call_args, name, value)

        return call_args


class ThriftRequest(object):

    __slots__ = (
        'service', 'endpoint', 'result_type', 'call_args', 'hostport',
        '_serializer',
    )

    # TODO - implement __repr__

    def __init__(self, service, endpoint, result_type,
                 call_args, hostport=None, serializer=None):

        self.service = service
        self.endpoint = endpoint
        self.result_type = result_type
        self.call_args = call_args
        self.hostport = hostport

        if not serializer:
            serializer = ThriftSerializer(self.result_type)
        self._serializer = serializer

    def get_serializer(self):
        return self._serializer

    def read_body(self, body):
        """Handles the response body for this request.

        If the response body includes a result, returns the result unwrapped
        from the response union. If the response contains an exception, raises
        that exception.
        """
        result_spec = self.result_type.thrift_spec

        # raise application exception, if present
        for exc_spec in result_spec[1:]:
            exc = getattr(body, exc_spec[2])
            if exc is not None:
                raise exc

        # success - non-void
        if len(result_spec) >= 1 and result_spec[0] is not None:

            # value expected, but got none
            # TODO - server side should use this same logic
            if body.success is None:
                raise ValueExpectedError(
                    'Expected a value to be returned for %s, '
                    'but recieved None - only void procedures can '
                    'return None.' % self.endpoint
                )

            return body.success

        # success - void
        else:
            return None


def _create_methods(thrift_module):

    # TODO - this method isn't needed, instead, do:
    #
    # for name in get_service_methods(...):
    #   method = _create_method(...)
    #     # ...
    #

    methods = {}
    method_names = get_service_methods(thrift_module.Iface)

    for method_name in method_names:

        method = _create_method(method_name)
        methods[method_name] = method

    return methods


def _create_method(method_name):

    # TODO - copy over entire signature using @functools.wraps(that_function)
    # or wrapt on Iface.<method>

    def method(self, *args, **kwargs):
        # TODO switch to __make_request
        return self._make_request(method_name, args, kwargs)

    return method
