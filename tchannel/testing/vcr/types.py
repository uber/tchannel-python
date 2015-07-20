from __future__ import absolute_import

from collections import namedtuple


class Request(namedtuple('Request', 'service endpoint headers body')):
    """VCR's view of the request.

    This only includes information necessary to match requests.
    """

    def to_primitive(self):
        return {
            'service': self.service,
            'endpoint': self.endpoint,
            'headers': self.headers,
            'body': self.body,
        }

    @classmethod
    def to_native(cls, data):
        return cls(
            service=data['service'],
            endpoint=data['endpoint'],
            headers=data['headers'],
            body=data['body'],
        )


class Response(namedtuple('Response', 'status headers body')):
    """VCR's view of the response.

    This only includes information necessary to reproduce responses.
    """

    def to_primitive(self):
        return {
            'status': self.status,
            'headers': self.headers,
            'body': self.body,
        }

    @classmethod
    def to_native(cls, data):
        return cls(
            status=data['status'],
            headers=data['headers'],
            body=data['body'],
        )


class Interaction(namedtuple('Interaction', 'request response')):
    """An interaction is a request-response pair."""

    def to_primitive(self):
        return {
            'request': self.request.to_primitive(),
            'response': self.response.to_primitive(),
        }

    @classmethod
    def to_native(cls, data):
        return cls(
            request=Request.to_native(data['request']),
            response=Response.to_native(data['response']),
        )
