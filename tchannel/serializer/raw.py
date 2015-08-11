from __future__ import absolute_import

from tchannel.schemes import RAW


class RawSerializer(object):
    def __init__(self):
        self.name = RAW

    def deserialize_header(self, obj):
        return obj

    def serialize_header(self, obj):
        return obj

    def deserialize_body(self, obj):
        return obj

    def serialize_body(self, obj):
        return obj
