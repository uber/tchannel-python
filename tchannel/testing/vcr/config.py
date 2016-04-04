# Copyright (c) 2016 Uber Technologies, Inc.
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
import inspect
import wrapt
import sys

from .cassette import Cassette
from .patch import Patcher, force_reset
from .server import VCRProxyService


class _CassetteContext(object):
    """Lets use_cassette be used as a context manager and a decorator."""

    def __init__(self, path, record_mode, inject, matchers):
        self.path = path
        self.record_mode = record_mode
        self.inject = inject
        self.matchers = matchers

        self._exit_stack = contextlib2.ExitStack()

    def __enter__(self):
        cassette = self._exit_stack.enter_context(
            Cassette(
                path=self.path,
                record_mode=self.record_mode,
                matchers=self.matchers,
            )
        )

        server = self._exit_stack.enter_context(
            VCRProxyService(cassette=cassette, unpatch=force_reset)
        )

        # TODO Maybe instead of using this instance of the TChannel client, we
        # should use the one being patched to make the requests?

        self._exit_stack.enter_context(Patcher(server.hostport))

        return cassette

    def __exit__(self, *args):
        self._exit_stack.__exit__(*args)

    def _handle_coroutine(self, function, args, kwargs):
        with self as cassette:
            if self.inject:
                coroutine = function(cassette, *args, **kwargs)
            else:
                coroutine = function(*args, **kwargs)

            # Spin the generator, yielding its results and sending back
            # respnoses and exceptions until it is exhausted. StopIteration
            # will be raised and caught by the caller (@gen.coroutine).
            future = next(coroutine)
            while True:
                try:
                    result = yield future
                except Exception:
                    future = coroutine.throw(*sys.exc_info())
                else:
                    future = coroutine.send(result)

    @wrapt.decorator
    def __call__(self, function, instance, args, kwargs):
        if inspect.isgeneratorfunction(function):
            return self._handle_coroutine(function, args, kwargs)

        with self as cassette:
            if self.inject:
                return function(cassette, *args, **kwargs)
            else:
                return function(*args, **kwargs)


def use_cassette(path, record_mode=None, inject=False, matchers=None):
    """Use or create a cassette to record/replay TChannel requests.

    This may be used as a context manager or a decorator.

    .. code-block:: python

        from tchannel.testing import vcr

        @pytest.mark.gen_test
        @vcr.use_cassette('tests/data/bar.yaml')
        def test_bar():
            channel = TChannel('test-client')
            service_client = MyServiceClient(channel)

            yield service_client.myMethod()


        def test_bar():
            with vcr.use_cassette('tests/data/bar.yaml', record_mode='none'):
                # ...

    Note that when used as a decorator on a coroutine, the ``use_cassette``
    decorator must be applied BEFORE ``gen.coroutine`` or
    ``pytest.mark.gen_test``.

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
    :param inject:
        If True, when ``use_cassette`` is used as a decorator, the cassette
        object will be injected into the function call as the first argument.
        Defaults to False.
    :param matchers:
        Used to configure the request attributes which VCR matches on. A
        recorded response will be replayed if all specified attributes of the
        corresponding request match the request that is being made. Valid
        attributes are: ``serviceName``, ``hostPort``, ``endpoint``,
        ``headers``, ``body``, ``argScheme``, and ``transportHeaders``.

        For example,

        .. code-block:: python

            MY_MATCHERS = list(vcr.DEFAULT_MATCHERS)
            MY_MATCHERS.remove('headers')

            @vcr.use_cassette('tests/data/foo.yaml', matchers=MY_MATCHERS):
            def test_foo():
                # ...

        By default, the following attributes are matched: ``serviceName``,
        ``endpoint``, ``headers``, ``body``, and ``argScheme``.
        :py:data:`tchannel.testing.vcr.DEFAULT_MATCHERS` is a tuple of all
        these matchers.
    """

    return _CassetteContext(
        path=path,
        record_mode=record_mode,
        inject=inject,
        matchers=matchers,
    )

    # TODO create some sort of configurable VCR object which implements
    # use_cassette. Top-level use_cassette can just use a default instance.


__all__ = ['use_cassette']
