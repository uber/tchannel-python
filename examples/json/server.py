from tornado import gen, ioloop

from tchannel import schemes
from tchannel.tornado import TChannel


app = TChannel('json-server', hostport='127.0.0.1:54496')


@app.register('endpoint', schemes.JSON)
@gen.coroutine
def health(request, response, proxy):

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
