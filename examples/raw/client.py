from tornado import gen, ioloop

from tchannel import TChannel


client = TChannel('raw-client')


@gen.coroutine
def make_request():

    resp = yield client.raw(
        service='10.32.160.131:52250',
        endpoint='health'
    )

    raise gen.Return(resp)


io_loop = ioloop.IOLoop.current()

resp = io_loop.run_sync(make_request)


# TODO impl __repr__
print resp.body
print resp.headers
print resp.transport
