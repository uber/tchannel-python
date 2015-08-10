from tornado import gen, ioloop

from tchannel import TChannel, Response


tchannel = TChannel('raw-server', hostport='localhost:54495')


@tchannel.raw.register
@gen.coroutine
def endpoint(request):

    assert request.headers == 'req headers'
    assert request.body == 'req body'

    return Response('resp body', headers='resp headers')


tchannel.listen()

print tchannel.hostport

ioloop.IOLoop.current().start()
