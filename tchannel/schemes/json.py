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
    def __call__(self, service, endpoint, body=None,
                 headers=None, timeout=None):

        if headers is None:
            headers = {}

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
        )

        # deserialize
        response.headers = json.loads(response.headers)
        response.body = json.loads(response.body)

        raise gen.Return(response)

    def stream(self):
        pass

    def register(self):
        pass
