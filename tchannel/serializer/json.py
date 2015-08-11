from __future__ import absolute_import

import json

from tchannel.schemes import JSON


class JsonSerializer(object):
    def __init__(self):
        self.name = JSON

    def deserialize_header(self, obj):
        if not obj:
            return None
        return json.loads(obj)

    def serialize_header(self, obj):
        if not obj:
            obj = {}
        return json.dumps(obj)

    def deserialize_body(self, obj):
        if not obj:
            return None
        return json.loads(obj)

    def serialize_body(self, obj):
        if not obj:
            obj = {}
        return json.dumps(obj)
