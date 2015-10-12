from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel.sync.singleton import TChannel
from tchannel.sync import TChannel as SyncTChannel
from tchannel.singleton import TChannel as AsyncSingleton
from tchannel.errors import SingletonNotPreparedError


def test_stored_seperately_from_async_singleton():

    AsyncSingleton.prepare('async-app')

    with pytest.raises(SingletonNotPreparedError):
        TChannel.get_instance()

    TChannel.prepare('sync-app')

    instance = TChannel.get_instance()

    assert isinstance(instance,  SyncTChannel)
    assert AsyncSingleton.get_instance() is not instance
