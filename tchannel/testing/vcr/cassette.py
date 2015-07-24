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

from itertools import chain
from collections import deque

from . import types
from . import yaml
from .exceptions import RequestNotFoundError
from .exceptions import UnsupportedVersionError
from .record_modes import RecordMode


__all__ = ['Cassette']


# Version of the storage format.
VERSION = 1


class Cassette(object):
    """Represents a series of recorded interactions."""

    def __init__(self, path, record_mode=None):
        """Initialize a new cassette.

        :param path:
            File path at which this cassette will be stored.
        :param record_mode:
            One of 'once', 'none', 'all', 'new_episodes'. See
            :py:class:`tchannel.testing.vcr.RecordMode`.
        """
        # TODO move documentation around
        record_mode = record_mode or RecordMode.ONCE
        if isinstance(record_mode, basestring):
            record_mode = RecordMode.from_name(record_mode)

        self.path = path

        # Whether the cassette was loaded from an existing YAML. If False,
        # this was a new cassette and the YAML file did not exist.
        self.existed = False

        self._record_mode = record_mode
        self._available = deque()
        self._played = deque()
        self._recorded = deque()

        self._load()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.save()

    @property
    def record_mode(self):
        """The record mode being used for this cassette."""
        return self._record_mode.name

    @property
    def write_protected(self):
        return not self._record_mode.can_record(self)

    @property
    def play_count(self):
        """Number of responses that have been replayed."""
        return len(self._played)

    @property
    def data(self):
        """Get all known data for this cassette."""

        return deque(
            chain(self._played, self._available, self._recorded)
        )

    def _load(self):
        try:
            with open(self.path, 'r') as f:
                data = f.read()
                self.existed = True
        except IOError:
            return  # nothing to read

        data = yaml.load(data)
        if not (data and 'interactions' in data):
            return  # file was probably empty

        if int(data['version']) != VERSION:
            raise UnsupportedVersionError(
                'Cassette at "%s" is an unsupported version of the '
                'format: version %s' % (self.path, str(data['version']))
            )

        self._available = [
            types.Interaction.to_native(i) for i in data['interactions']
        ]

    def save(self):
        if not self._recorded:
            return

        # Order:
        # - things that were played in the order that were played
        # - things that haven't been played yet -- assuming the record mode
        #   allows it.
        # - things that were recorded in this session
        interactions = deque(self._played)
        if self._record_mode.save_unplayed:
            interactions.extend(self._available)
        interactions.extend(self._recorded)

        data = yaml.dump(
            {
                'interactions': [i.to_primitive() for i in interactions],
                'version': VERSION,
            }
        )

        with open(self.path, 'w') as f:
            f.write(data)

        self._played = deque()
        self._available = interactions
        self._recorded = deque()

    def can_replay(self, request):
        if not self._record_mode.replayable:
            return False
        for interaction in self._available:
            # TODO request matchers
            if interaction.request == request:
                return True
        return False

    def replay(self, request):
        assert self._record_mode.replayable, (
            'The record mode for this cassette prevents it from replaying '
            'requests'
        )

        for interaction in self._available:
            # TODO request matchers
            if interaction.request == request:
                self._available.remove(interaction)
                self._played.append(interaction)
                return interaction.response

        raise RequestNotFoundError(
            'Could not find a recorded response for %s' % repr(request)
        )

    def record(self, request, response):
        assert not self.write_protected, (
            'The record mode for this cassette prevents it from recording '
            'new requests'
        )
        self._recorded.append(types.Interaction(request, response))
