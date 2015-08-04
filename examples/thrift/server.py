from tornado import gen
from tornado.ioloop import IOLoop

from tchannel.tornado import TChannel

from tests.data.generated.ThriftTest import ThriftTest

app = TChannel('thrift-server')


@app.register(ThriftTest)
@gen.coroutine
def testString(request, response, tchannel):

    # TODO different than other schemes...
    response.write_header('hey', 'jane')

    return request.args.thing


app.listen()

print app.hostport

io_loop = IOLoop.current()
io_loop.start()
