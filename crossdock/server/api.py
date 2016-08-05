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

from collections import namedtuple

# Must match with corresponding constants in Go/Java/... projects
BAGGAGE_KEY = "crossdock-baggage-key"


# Request instructs the server to call another server recursively
# if Downstream is not None, and return the results of the downstream call
# as well as the current tracing span it observes in its Context.
Request = namedtuple('Request', ['serverRole', 'downstream'])

# Downstream describes which downstream service to call recursively.
Downstream = namedtuple(
    'Downstream',
    ['serviceName', 'serverRole', 'encoding', 'hostPort', 'downstream'])

# Response contains the span observed by the server and nested downstream
# response (which could be None).
Response = namedtuple('Response', ['span', 'downstream'])

# ObservedSpan describes the tracing span observed by the server.
ObservedSpan = namedtuple('ObservedSpan', ['traceId', 'sampled', 'baggage'])


def namedtuple_from_dict(json, tuple_cls):
    return tuple_cls(**{f: json[f] for f in tuple_cls._fields})


def request_from_dict(json):
    json['downstream'] = downstream_from_dict(json.get('downstream'))
    return namedtuple_from_dict(json, Request)


def downstream_from_dict(json):
    if json is None:
        return None
    json['downstream'] = downstream_from_dict(json.get('downstream'))
    return namedtuple_from_dict(json, Downstream)


def namedtuple_to_dict(tpl):
    json = {}
    for k, v in tpl._asdict().iteritems():
        if hasattr(v, '_asdict'):
            v = namedtuple_to_dict(v)
        json[k] = v
    return json


def response_from_dict(json):
    if json is None:
        return None
    json['span'] = namedtuple_from_dict(json.get('span'), ObservedSpan)
    json['downstream'] = response_from_dict(json.get('downstream'))
    return namedtuple_from_dict(json, Response)


