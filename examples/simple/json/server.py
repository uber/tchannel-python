from tornado import gen, ioloop

from tchannel import TChannel, schemes


app = TChannel('json-server', hostport='localhost:54496')


@app.register('endpoint', schemes.JSON)
@gen.coroutine
def endpoint(request, response, proxy):

    header = yield request.get_header()
    body = yield request.get_body()

    assert header == {
        'req': 'header',
    }
    assert body == {
        'req': 'body',
    }

    response.write_header({
        'resp': 'header',
    })
    response.write_body({
        'resp': 'body',
    })


app.listen()

print app.hostport

ioloop.IOLoop.current().start()
