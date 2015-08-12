from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from . import RAW


class RawArgScheme(object):
    """Semantic params and serialization for raw."""

    NAME = RAW

    def __init__(self, tchannel):
        self._tchannel = tchannel

    def __call__(self, service, endpoint, body=None, headers=None,
                 timeout=None, retry_on=None, retry_limit=None, hostport=None):
        """Make Raw TChannel Request.

        .. code-block: python

            from tchannel import TChannel

            tchannel = TChannel('my-service')

            resp = tchannel.raw(
                service='some-other-service',
                endpoint='get-all-the-crackers',
            )

        :param string service:
            Name of the service to call.
        :param string endpoint:
            Endpoint to call on service.
        :param string body:
            A raw body to provide to the endpoint.
        :param string headers:
            A raw headers block to provide to the endpoint.
        :param int timeout:
            How long to wait before raising a ``TimeoutError`` - this
            defaults to ``tchannel.glossary.DEFAULT_TIMEOUT``.
        :param string retry_on:
            What events to retry on - valid values can be found in
            ``tchannel.retry``.
        :param string retry_limit:
            How many times to retry before
        :param string hostport:
            A 'host:port' value to use when making a request directly to a
            TChannel service, bypassing Hyperbahn.
        :return Response:
        """

        return self._tchannel.call(
            scheme=self.NAME,
            service=service,
            arg1=endpoint,
            arg2=headers,
            arg3=body,
            timeout=timeout,
            retry_on=retry_on,
            retry_limit=retry_limit,
            hostport=hostport,
        )

    def register(self, endpoint, **kwargs):


        # no args, eg - server.raw.register
        if callable(endpoint):
            handler = endpoint
            endpoint = None

        # args, eg - server.raw.register('foo')
        else:
            handler = None


        # server.raw.register(endpoint="foo", handler=bar)

        # @server.raw.register
        # def bar():
        # => server.raw.register(handler)

        # @servre.raw.register(endpoint="foo")
        # def bar():
        #  pass

        # server.raw.register("foo")(bar)

        return self._tchannel.register(
            scheme=self.NAME,
            endpoint=endpoint,
            handler=handler,
            **kwargs
        )
