import json

from tornado import gen, ioloop

from tchannel import TChannel


tchannel = TChannel('json-client')


@gen.coroutine
def make_request():

    resp = yield tchannel.json(
        service='json-server',
        endpoint='endpoint',
        body={
            'req': 'body'
        },
        headers={
            'req': 'header'
        },
        hostport='127.0.0.1:54496',
    )

    raise gen.Return(resp)


resp = ioloop.IOLoop.current().run_sync(make_request)

assert resp.headers == {
    'resp': 'header',
}
assert resp.body == {
    'resp': 'body',
}

print json.dumps(resp.body)
print json.dumps(resp.headers)
