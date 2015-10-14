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

import pytest
import tornado
import tornado.gen

from tchannel import TChannel, Response
from tchannel.schemes import JSON
from tests.mock_server import MockServer


@pytest.fixture
def sample_json():
    body = [
        {
            "age": 37,
            "company": "IMANT",
            "email": "cummingsbritt@imant.com",
            "friends": [
                {
                    "id": 0,
                    "name": "Meyer Shields"
                },
                {
                    "id": 1,
                    "name": "Shelia Patterson"
                },
                {
                    "id": 2,
                    "name": "Franco Spencer"
                }
            ],
            "latitude": 46.911329,
            "longitude": 133.490945,
            "phone": "+1 (978) 509-2329",
            "registered": "2014-10-19T15:05:42 +07:00",
            "tags": [
                "a",
                "bmollit",
                "caute",
                "daliqua",
                "epariatur",
                "fut",
            ]
        }
    ]

    return body


def register(tchannel):
    @tchannel.json.register("json_echo")
    @tornado.gen.coroutine
    def json_echo(request):
        headers = request.headers
        body = request.body

        return Response(body, headers)


@pytest.yield_fixture
def json_server():
    with MockServer() as server:
        register(server.tchannel)
        yield server


@pytest.mark.gen_test
def test_json_server(json_server, sample_json):
    endpoint = "json_echo"
    tchannel = TChannel(name='test')

    header = {'ab': 'bc'}
    body = sample_json
    resp = yield tchannel.json(
        service='endpoint1',
        hostport=json_server.hostport,
        endpoint=endpoint,
        headers=header,
        body=body,
    )

    # check protocol header
    assert resp.transport.scheme == JSON
    # compare header's json
    assert resp.headers == header

    # compare body's json
    assert resp.body == body
