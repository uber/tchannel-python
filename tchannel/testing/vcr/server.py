from __future__ import absolute_import

from tornado import gen

from tchannel.tornado import TChannel

from . import types


class FakeServer(object):
    """A fake TChannel server to record or replay requests."""

    def __init__(self, cassette, real_peer):
        self.cassette = cassette
        self.real_peer = real_peer
        self.tchannel = TChannel('fake-server')

        self.tchannel.register(
            endpoint=self.tchannel.FALLBACK,
            handler=self.handle_request
        )

    @gen.coroutine
    def handle_request(self, req, res, channel):
        endpoint = req.endpoint
        headers = yield req.get_header()
        body = yield req.get_body()

        request = types.Request(req.service, endpoint, headers, body)

        # TODO decode requests and responses based on arg scheme into more
        # readable formats.

        if self.cassette.can_replay(request):
            response = self.cassette.replay(request)
            res.status_code = response.status
            res.write_header(response.headers)
            res.write_body(response.body)
            return

        # TODO propagate other request and response parameters
        # TODO record modes

        real_response = yield self.real_peer.request(
            request.service,
            arg_scheme=req.arg_scheme,
            hostport=self.real_peer.hostport,
            retry='n',
            # TODO other parameters
        ).send(
            request.endpoint,
            request.headers,
            request.body,
            headers=req.headers,  # protocol headers
        )

        res_headers = yield real_response.get_header()
        res_body = yield real_response.get_body()

        response = types.Response(
            real_response.status_code, res_headers, res_body
        )
        self.cassette.record(request, response)

        res.status_code = response.status
        res.write_header(response.headers)
        res.write_body(response.body)

    @property
    def hostport(self):
        return self.tchannel.hostport

    def start(self):
        self.tchannel.listen()

    def stop(self):
        self.tchannel.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
