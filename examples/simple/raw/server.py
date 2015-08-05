from tornado import gen, ioloop

from tchannel.tornado import TChannel


app = TChannel('raw-server', hostport='127.0.0.1:54495')


@app.register('endpoint')
@gen.coroutine
def endpoint(request, response, proxy):

    header = yield request.get_header()
    body = yield request.get_body()

    assert header == 'req headers'
    assert body == 'req body'

    response.write_header('resp header')
    response.write_body('resp body')


app.listen()

print app.hostport

ioloop.IOLoop.current().start()
