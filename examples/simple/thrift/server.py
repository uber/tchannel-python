from __future__ import absolute_import

from tornado import gen, ioloop
from tchannel import TChannel, Response
from tchannel.testing.data.generated.ThriftTest import ThriftTest


tchannel = TChannel('thrift-server', hostport='localhost:54497')


@tchannel.thrift.register(ThriftTest)
@gen.coroutine
def testString(request):

    assert request.headers == {'req': 'header'}
    assert request.body.thing == 'req'

    return Response('resp', headers={'resp': 'header'})


tchannel.listen()

print tchannel.hostport

ioloop.IOLoop.current().start()
