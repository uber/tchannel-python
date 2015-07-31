from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import types

from .util import get_service_methods


def from_thrift_module(service, thrift_module):

    # start building requests instance
    maker = ThriftRequestMaker(service, thrift_module)

    # create methods that mirror thrift client
    # and each return ThriftRequest
    methods = _create_methods(thrift_module)

    # attach to maker
    for name, method in methods.iteritems():
        method = types.MethodType(method, maker, ThriftRequestMaker)
        setattr(maker, name, method)

    return maker


class ThriftRequestMaker(object):

    prop = "SUP"

    def __init__(self, service, thrift_module):
        self.service = service
        self.thrift_module = thrift_module

    def _make_request(self, method_name, args, kwargs):

        print(method_name)
        print(args)
        print(kwargs)

        endpoint = '%s::%s' % (self.service, method_name)
        args_type = getattr(self.thrift_module, method_name + '_args')
        result_type = getattr(self.thrift_module, method_name + '_result')

        # TODO just pass to self._get_request()
        # instead and keep this fn thin? get working first...

        request = ThriftRequest(
            service=self.service,
            endpoint=endpoint,
            args_type=args_type,
            result_type=result_type
        )

        return request


class ThriftRequest(object):

    def __init__(self, service, endpoint, args_type, result_type):
        self.service = service
        self.endpoint = endpoint
        self.args_type = args_type
        self.result_type = result_type


def _create_methods(thrift_module):

    methods = {}
    method_names = get_service_methods(thrift_module.Iface)

    for method_name in method_names:

        method = _create_method(method_name)
        methods[method_name] = method
        print(method_name)

    return methods


def _create_method(method_name):

    def method(self, *args, **kwargs):
        # TODO switch to __make_request
        return self._make_request(method_name, args, kwargs)

    return method
