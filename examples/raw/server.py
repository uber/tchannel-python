from tornado.ioloop import IOLoop

from tchannel.tornado import TChannel


app = TChannel('raw-server')


@app.register('health')
def health(request, response, tchannel):

    # TODO should be able to return body no matter the scheme
    response.write_body('OK')


app.listen()

print app.hostport

io_loop = IOLoop.current()
io_loop.start()
