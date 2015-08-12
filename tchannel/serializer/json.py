from __future__ import absolute_import

import json

from tchannel.schemes import JSON


class JsonSerializer(object):
    name = JSON

    def deserialize_header(self, obj):
        if obj:
            return json.loads(obj)

    def serialize_header(self, obj):
        if obj:
            return json.dumps(obj)

    def deserialize_body(self, obj):
        return json.loads(obj)

    def serialize_body(self, obj):
        return json.dumps(obj)
