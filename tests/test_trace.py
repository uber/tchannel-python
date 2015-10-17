from __future__ import absolute_import

import pytest

from tchannel import TChannel, schemes
from tchannel.errors import BadRequestError
from tchannel.event import EventHook


@pytest.mark.gen_test
def test_error_trace():
    tchannel = TChannel('test')

    class ErrorEventHook(EventHook):
        def __init__(self):
            self.request_trace = None
            self.error_trace = None

        def before_receive_request(self, request):
            self.request_trace = request.tracing

        def after_send_error(self, error):
            self.error_trace = error.tracing

    hook = ErrorEventHook()
    tchannel.hooks.register(hook)

    tchannel.listen()

    with pytest.raises(BadRequestError):
        yield tchannel.call(
            scheme=schemes.RAW,
            service='test',
            arg1='endpoint',
            hostport=tchannel.hostport,
            timeout=0.02,
        )

    assert hook.error_trace
    assert hook.request_trace
    assert hook.error_trace == hook.request_trace
