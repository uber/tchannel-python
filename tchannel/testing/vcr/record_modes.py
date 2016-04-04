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

from .exceptions import VCRError

__all__ = ['RecordMode']


class _RecordMode(object):
    """A _RecordMode dictates a cassette's behavior on recording and replays.

    :param name:
        Name of the record mode.
    :param replayable:
        Whether this record mode allows requests to be replayed.
    :param can_record:
        Whether this record mode allows new interactions to be recorded. This
        may be a boolean or a function that accepts the cassette and returns a
        boolean.
    :param save_unplayed:
        Whether the cassette remembers previously saved unplayed interactions
        when the cassette is saved again. This is useful when the record mode
        needs to forget unused interactions.
    """

    __slots__ = ('name', 'replayable', 'can_record', 'save_unplayed')

    def __init__(self, name, replayable, can_record, save_unplayed):
        self.name = name
        self.replayable = replayable
        self.save_unplayed = save_unplayed
        if not callable(can_record):
            self.can_record = (lambda _: can_record)
        else:
            self.can_record = can_record


class RecordMode(object):
    """
    Record modes dictate how a cassette behaves when interactions are replayed
    or recorded. The following record modes are supported.

    .. autoattribute:: ONCE
       :annotation: = 'once'

    .. autoattribute:: NEW_EPISODES
       :annotation: = 'new_episodes'

    .. autoattribute:: NONE
       :annotation: = 'none'

    .. autoattribute:: ALL
       :annotation: = 'all'
    """

    #: If the YAML file did not exist, record new interactions and save them.
    #: If the YAML file already existed, replay existing interactions but
    #: disallow any new interactions. This is the default and usually what you
    #: want.
    ONCE = _RecordMode(
        name='once',
        replayable=True,
        can_record=(lambda c: not c.existed),
        save_unplayed=True,
    )

    #: Replay existing interactions and allow recording new ones. This is
    #: usually undesirable since it reduces predictability in tests.
    NEW_EPISODES = _RecordMode(
        name='new_episodes',
        replayable=True,
        can_record=True,
        save_unplayed=True,
    )

    #: Replay existing interactions and disallow any new interactions.  This
    #: is a good choice for tests whose behavior is unlikely to change in the
    #: near future. It ensures that those tests don't accidentally start
    #: making new requests.
    NONE = _RecordMode(
        name='none',
        replayable=True,
        can_record=False,
        save_unplayed=True,
    )

    #: Do not replay anything and record all new interactions. Forget all
    #: existing interactions. This may be used to record everything anew.
    ALL = _RecordMode(
        name='all',
        replayable=False,
        can_record=True,
        save_unplayed=False,
    )

    @classmethod
    def from_name(cls, name):
        """Get a RecordMode by its name."""
        name = name.lower()

        if name not in _MODES:
            raise VCRError(
                'Invalid record mode %s. It must be one of "once", "none", '
                '"all", or "new_episodes". Check the documentation for more '
                'information' % repr(name)
            )
        return _MODES[name]


_MODES = {m.name.lower(): m for m in [
    RecordMode.ONCE, RecordMode.NEW_EPISODES, RecordMode.NONE, RecordMode.ALL
]}
