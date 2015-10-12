from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel as AsyncTChannel
from tchannel.singleton import TChannel
from tchannel.errors import SingletonNotPreparedError


def test_get_instance_is_singleton():
    TChannel.prepare('my-app')
    assert TChannel.get_instance() is TChannel.get_instance()
    TChannel.reset()


def test_must_call_prepare_before_get_instance():
    with pytest.raises(SingletonNotPreparedError):
        TChannel.get_instance()


def test_get_instance_returns_configured_tchannel():

    TChannel.prepare('my-app')

    tchannel = TChannel.get_instance()

    assert isinstance(tchannel, AsyncTChannel)
    assert tchannel.name == 'my-app'

    TChannel.reset()
