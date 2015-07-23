"""This module provides VCR-like functionality for TChannel.

.. code-block:: python

    from tchannel.testing import vcr

    @vcr.use_cassette('tests/data/foo.yaml')
    def test_foo():
        channel = TChannel('test-client')
        service_client = MyServiceClient(channel)

        yield service_client.myMethod()

It is heavily inspired by the `vcrpy <https://github.com/kevin1024/vcrpy/>`_
library.
"""
from __future__ import absolute_import

from .patch import Patcher
from .cassette import Cassette


def use_cassette(path):
    # TODO create some sort of configurable VCR object which implements
    # use_cassette. Top-level use_cassette can just use a default instance.
    return Patcher(Cassette(path))


__all__ = ['use_cassette']
