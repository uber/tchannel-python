# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
VCR
===

``tchannel.testing.vcr`` provides VCR-like functionality for TChannel. It is
heavily inspired by the `vcrpy <https://github.com/kevin1024/vcrpy/>`_
library.

This allows recording TChannel requests and their responses into YAML files
during integration tests and replaying those recorded responses when the tests
are run next time.

The simplest way to use this is with the :py:func:`use_cassette` function.

.. autofunction:: use_cassette

Configuration
-------------

.. _record-modes:

Record Modes
~~~~~~~~~~~~

Record modes dictate how a cassette behaves when interactions are replayed or
recorded. The following record modes are supported.

once
    If the YAML file did not exist, record new interactions and save them.  If
    the YAML file already existed, replay existing interactions but disallow
    any new interactions. This is the default and usually what you want.
none
    Replay existing interactions and disallow any new interactions.  This is
    a good choice for tests whose behavior is unlikely to change in the near
    future. It ensures that those tests don't accidentally start making new
    requests.
all
    Record all interactions. Do not replay anything. This is useful for
    re-recording everything anew.
new_episodes
    Replay existing interactions and allow recording new ones. This is usually
    undesirable since it reduces predictability in tests.
"""
from __future__ import absolute_import

from .patch import Patcher
from .cassette import Cassette


def use_cassette(path, record_mode=None):
    """Use or create a cassette to record/replay TChannel requests.

    This may be used as a context manager or a decorator.

    .. code-block:: python

        from tchannel.testing import vcr

        @vcr.use_cassette('tests/data/foo.yaml')
        def test_foo():
            channel = TChannel('test-client')
            service_client = MyServiceClient(channel)

            yield service_client.myMethod()


        def test_bar():
            with vcr.use_cassette('tests/data/bar.yaml'):
                # ...

    :param path:
        Path to the cassette. If the cassette did not already exist, it will
        be created. If it existed, its contents will be replayed (depending on
        the record mode).
    :param record_mode:
        The record mode dictates whether a cassette is allowed to record or
        replay interactions. This must be one of "once", "none", "all", or
        "new_episodes". Defaults to "once". See :ref:`record-modes` for
        details on supported record modes and how to use them.
    """
    # TODO create some sort of configurable VCR object which implements
    # use_cassette. Top-level use_cassette can just use a default instance.
    return Patcher(Cassette(path=path, record_mode=record_mode))


__all__ = ['use_cassette']
