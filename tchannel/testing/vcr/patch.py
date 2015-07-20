from __future__ import absolute_import

from functools import wraps

import mock
from contextlib2 import ExitStack, contextmanager

from tchannel.tornado import peer

from .server import FakeServer


_PeerGroup_choose = peer.PeerGroup.choose


class Patcher(object):

    def __init__(self, cassette):
        self.cassette = cassette
        self._exit_stack = ExitStack()

    @contextmanager
    def _patch_choose(self):

        # TODO the choose() implementation should prodably be moved elsewhere

        def choose(group, *args, **kwargs):
            real_peer = _PeerGroup_choose(group, *args, **kwargs)
            server = FakeServer(self.cassette, real_peer)

            # This starts the fake server. The server will stop when the
            # system exits the Patcher context.
            self._exit_stack.enter_context(server)

            # Return a Peer pointing to the fake server instead. The server
            # will forward the request to the real peer if it can't replay it.
            fake_peer = _PeerGroup_choose(group, hostport=server.hostport)

            # TODO It may be worth creating a proxy object that redirects all
            # but the .send calls to the real peer.
            return fake_peer

        # TODO investigate if something other than choose can be patched
        # instead, or investigate how this interacts with TCollector, etc.
        with mock.patch.object(peer.PeerGroup, 'choose', choose):
            yield

    def __enter__(self):
        self._exit_stack.enter_context(self._patch_choose())
        return self.cassette

    def __exit__(self, *args):
        self.cassette.save()
        self._exit_stack.close()

    def __call__(self, function):
        # being used as a decorator

        @wraps(function)
        def new_function(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        return new_function
