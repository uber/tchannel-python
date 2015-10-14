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
from collections import namedtuple

from . import yaml
from .exceptions import RequestNotFoundError
from .exceptions import UnsupportedVersionError
from .record_modes import RecordMode
from . import proxy

__all__ = ['Cassette', 'DEFAULT_MATCHERS']


# Version of the storage format.
VERSION = 1


class Interaction(namedtuple('Interaction', 'request response')):
    """An interaction is a request-response pair."""

    def to_primitive(self):
        return {
            'request': self.request.to_primitive(),
            'response': self.response.to_primitive(),
        }

    @classmethod
    def to_native(cls, data):
        return cls(
            request=proxy.Request.from_primitive(data['request']),
            response=proxy.Response.from_primitive(data['response']),
        )


def attrmatcher(name):
    "A matcher that matches if the given attribute is equal for both values."

    def matcher(left, right):
        return getattr(left, name) == getattr(right, name)

    return matcher

# A dictionary from matcher name to matcher.
#
# A matcher is a function that takes two arguments and returns true if they
# match.
#
# The dictionary contains all known matchers.
_MATCHERS = {
    n: attrmatcher(n) for n in (
        'serviceName', 'hostPort', 'endpoint', 'headers', 'body', 'argScheme',
        'transportHeaders',
    )
}


DEFAULT_MATCHERS = (
    'serviceName', 'endpoint', 'headers', 'body', 'argScheme',
)


class Cassette(object):
    """Represents a series of recorded interactions."""

    def __init__(self, path, record_mode=None, matchers=None):
        """Initialize a new cassette.

        :param path:
            File path at which this cassette will be stored.
        :param record_mode:
            One of 'once', 'none', 'all', 'new_episodes'. See
            :py:class:`tchannel.testing.vcr.RecordMode`.
        :param matchers:
            If specified, this is a collection of matcher names. These
            specify which attributes on two requests should match for them to
            be considered equal.
        """
        # TODO move documentation around
        record_mode = record_mode or RecordMode.ONCE
        if isinstance(record_mode, basestring):
            record_mode = RecordMode.from_name(record_mode)

        self.path = path

        # Whether the cassette was loaded from an existing YAML. If False,
        # this was a new cassette and the YAML file did not exist.
        self.existed = False

        if matchers is None:
            matchers = DEFAULT_MATCHERS

        self._matchers = []
        for m in matchers:
            try:
                self._matchers.append(_MATCHERS[m])
            except KeyError:
                raise KeyError('%s is not a known matcher' % m)

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

    def _match(self, left, right):
        return all(m(left, right) for m in self._matchers)

    def _find(self, request, haystack=None):
        "A generator that returns yields matching interactions for a request"

        haystack = haystack or self._available

        for interaction in haystack:
            if self._match(request, interaction.request):
                yield interaction

    def _load(self):
        try:
            with open(self.path, 'rb') as f:
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
            Interaction.to_native(i) for i in data['interactions']
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

        with open(self.path, 'wb') as f:
            f.write(data)

        self._played = deque()
        self._available = interactions
        self._recorded = deque()

    def can_replay(self, request):
        if not self._record_mode.replayable:
            return False
        try:
            next(self._find(request))
        except StopIteration:
            return False
        else:
            return True

    def replay(self, request):
        assert self._record_mode.replayable, (
            'The record mode for this cassette prevents it from replaying '
            'requests'
        )

        for interaction in self._find(request):
            # TODO request matchers
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
        self._recorded.append(Interaction(request, response))
