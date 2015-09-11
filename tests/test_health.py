from __future__ import absolute_import

import pytest

from tchannel import TChannel, thrift_request_builder
from tchannel.health.thrift import Meta
from tchannel.health import HealthStatus


@pytest.mark.gen_test
def test_default_health():
    server = TChannel("health_test_server")
    server.listen()

    client = TChannel("health_test_client")
    service = thrift_request_builder(
        service='meta',
        thrift_module=Meta,
        hostport=server.hostport,
    )
    resp = yield client.thrift(request=service.health())
    assert resp.body.ok is True
    assert resp.body.message is None


def user_health(request):
    return HealthStatus(ok=False, message="from me")


@pytest.mark.gen_test
def test_user_health():
    server = TChannel("health_test_server")
    server.register_health_handler(user_health, method='health')
    server.listen()

    client = TChannel("health_test_client")
    service = thrift_request_builder(
        service='meta',
        thrift_module=Meta,
        hostport=server.hostport,
    )
    resp = yield client.thrift(request=service.health())
    assert resp.body.ok is False
    assert resp.body.message == "from me"
