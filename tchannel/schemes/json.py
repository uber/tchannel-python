from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json

from tornado import gen

from . import JSON


class JsonArgScheme(object):
    """Semantic params and serialization for json."""

    NAME = JSON

    def __init__(self, tchannel):
        self._tchannel = tchannel

    @gen.coroutine
    def __call__(self, service, endpoint, body=None, headers=None,
                 timeout=None, retry_on=None, retry_limit=None, hostport=None):
        """Make JSON TChannel Request.

        .. code-block: python

            from tchannel import TChannel

            tchannel = TChannel('my-service')

            resp = tchannel.json(
                service='some-other-service',
                endpoint='get-all-the-crackers',
                body={
                    'some': 'dict',
                },
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

        # TODO should we not default these?
        if headers is None:
            headers = {}

        # TODO dont default?
        if body is None:
            body = {}

        # serialize
        headers = json.dumps(headers)
        body = json.dumps(body)

        response = yield self._tchannel.call(
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

        # deserialize
        response.headers = json.loads(response.headers)
        response.body = json.loads(response.body)

        raise gen.Return(response)
