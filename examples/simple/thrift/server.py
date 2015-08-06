from __future__ import absolute_import

from tornado import gen, ioloop
from tchannel import TChannel
from tchannel.testing.data.generated.ThriftTest import ThriftTest


app = TChannel('thrift-server', hostport='localhost:54497')


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
