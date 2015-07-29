from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json

from tornado import gen

from . import JSON
from .base import BaseFormat


class JsonFormat(BaseFormat):

    NAME = JSON

    @gen.coroutine
    def call(self, service, endpoint, body=None,
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
