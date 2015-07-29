from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json

from tornado import gen

from . import JSON


class JsonFormat(object):
    """Semantic params and serialization for json."""

    NAME = JSON

    def __init__(self, tchannel):
        self.tchannel = tchannel

    @gen.coroutine
    def __call__(self, service, endpoint, body=None,
                 headers=None, timeout=None):

        if body is None:
            body = {}

        body = json.dumps(body)

        response = yield self.tchannel.call(
            format=self.NAME,
            service=service,
            arg1=endpoint,
            arg2=headers,
            arg3=body,
            timeout=timeout,
        )

        response.body = json.loads(response.body)

        raise gen.Return(response)

    def stream(self):
        pass
