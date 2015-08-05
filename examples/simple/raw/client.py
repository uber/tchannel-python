from tornado import gen, ioloop

from tchannel import TChannel


tchannel = TChannel('raw-client')


@gen.coroutine
def make_request():

    resp = yield tchannel.raw(
        service='raw-server',
        endpoint='endpoint',
        body='req body',
        headers='req headers',
        hostport='127.0.0.1:54495',
    )

    raise gen.Return(resp)


resp = ioloop.IOLoop.current().run_sync(make_request)

assert resp.headers == 'resp headers'
assert resp.body == 'resp body'

print resp.body
print resp.headers
