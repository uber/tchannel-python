from tornado import gen, ioloop

from tchannel.tornado import TChannel

from tests.data.generated.ThriftTest import ThriftTest


app = TChannel('thrift-server', hostport='127.0.0.1:54497')


@app.register(ThriftTest)
@gen.coroutine
def testString(request, response, tchannel):

    assert request.headers == [['req', 'header']]
    assert request.args.thing == 'req'

    response.write_header('resp', 'header')
    response.write_result('resp')


app.listen()

print app.hostport

ioloop.IOLoop.current().start()
