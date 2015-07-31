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

from __future__ import absolute_import

import contextlib2

from tchannel.tornado import TChannel
from tchannel.thrift import client_for

from .cassette import Cassette
from .patch import Patcher, force_reset
from .server import VCRProxyService, VCRProxy


VCRProxyClient = client_for('vcr', VCRProxy)


@contextlib2.contextmanager
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
            with vcr.use_cassette('tests/data/bar.yaml', record_mode='none'):
                # ...

    :param path:
        Path to the cassette. If the cassette did not already exist, it will
        be created. If it existed, its contents will be replayed (depending on
        the record mode).
    :param record_mode:
        The record mode dictates whether a cassette is allowed to record or
        replay interactions. This may be a string specifying the record mode
        name or an element from the
        :py:class:`tchannel.testing.vcr.RecordMode` object. This parameter
        defaults to :py:attr:`tchannel.testing.vcr.RecordMode.ONCE`. See
        :py:class:`tchannel.testing.vcr.RecordMode` for details on supported
        record modes and how to use them.
    """

    # TODO create some sort of configurable VCR object which implements
    # use_cassette. Top-level use_cassette can just use a default instance.

    with contextlib2.ExitStack() as exit_stack:
        cassette = exit_stack.enter_context(
            Cassette(path=path, record_mode=record_mode)
        )

        server = exit_stack.enter_context(
            VCRProxyService(cassette=cassette, unpatch=force_reset)
        )

        # TODO Maybe instead of using this instance of the TChannel client, we
        # should use the one being patched to make the requests?
        client = VCRProxyClient(
            tchannel=TChannel('proxy-client'),
            hostport=server.hostport,
        )
        exit_stack.enter_context(Patcher(client))

        yield cassette


__all__ = ['use_cassette']
