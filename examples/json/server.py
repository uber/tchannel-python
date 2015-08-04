from tornado import gen
from tornado.ioloop import IOLoop

from tchannel.tornado import TChannel
from tchannel import schemes


app = TChannel('json-server')


@app.register('health', schemes.JSON)
@gen.coroutine
def health(request, response, tchannel):

    # TODO in thrift you dont have to yield...
    body = yield request.get_body()

    # TODO should be get_headers()
    headers = yield request.get_header()

    # TODO should be write_headers()
    response.write_header(headers)

    # TODO should be able to return body no matter the scheme
    response.write_body({
        'health': 'OK',
        'body': body,
    })


app.listen()

print app.hostport

io_loop = IOLoop.current()
io_loop.start()
