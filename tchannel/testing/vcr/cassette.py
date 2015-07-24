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


# Version of the storage format.
VERSION = 1


class Cassette(object):
    """Represents a series of recorded interactions."""

    def __init__(self, path):
        """Initialize a new cassette.

        :param path:
            File path at which this cassette will be stored.
        """
        self.path = path

        # Number of times interactions from this cassette have been played.
        self.play_count = 0

        self._available = deque()
        self._played = deque()
        self._recorded = deque()

        self._load()

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
        except IOError:
            return  # nothing to read

        data = yaml.load(data)
        if 'interactions' in data:
            if int(data['version']) != VERSION:
                raise UnsupportedVersionError(
                    ('Cassette at "%s" is an unsupported version of the '
                     'format: version %s') % (self.path, str(data['version']))
                )
            self._available = [
                types.Interaction.to_native(i) for i in data['interactions']
            ]

    def save(self):
        if not self._recorded:
            return

        interactions = self.data
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
        for interaction in self._available:
            # TODO request matchers
            if interaction.request == request:
                return True
        return False

    def replay(self, request):
        for interaction in self._available:
            # TODO request matchers
            if interaction.request == request:
                self._available.remove(interaction)
                self._played.append(interaction)
                self.play_count += 1
                return interaction.response

        raise RequestNotFoundError(
            'Could not find a recorded response for %s' % repr(request)
        )

    def record(self, request, response):
        self._recorded.append(types.Interaction(request, response))
