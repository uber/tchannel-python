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
                 header=None, timeout=None):

        if header is None:
            header = {}

        if body is None:
            body = {}

        # serialize
        header = json.dumps(header)
        body = json.dumps(body)

        response = yield self.tchannel.call(
            format=self.NAME,
            service=service,
            arg1=endpoint,
            arg2=header,
            arg3=body,
            timeout=timeout,
        )

        # deserialize
        response.header = json.loads(response.header)
        response.body = json.loads(response.body)

        raise gen.Return(response)

    def stream(self):
        pass
