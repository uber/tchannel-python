from tornado import gen, ioloop

from tchannel import TChannel


client = TChannel('json-client')
service = '10.32.160.131:52275'


@gen.coroutine
def make_request():

    resp = yield client.json(
        service=service,
        endpoint='health',
        body={
            'boomboomboom': 'hearyousaywayo'
        },
        headers={
            'bobby': 'twotoes'
        }
    )

    raise gen.Return(resp)


io_loop = ioloop.IOLoop.current()

resp = io_loop.run_sync(make_request)


# TODO impl __repr__
print resp.body
print resp.headers
print resp.transport
