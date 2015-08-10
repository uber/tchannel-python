from tornado import gen, ioloop

from tchannel import TChannel, Response


tchannel = TChannel('json-server', hostport='localhost:54496')


@tchannel.json.register
@gen.coroutine
def endpoint(request):

    assert request.headers == {'req': 'header'}
    assert request.body == {'req': 'body'}

    return Response({'resp': 'body'}, headers={'resp': 'header'})


tchannel.listen()

print tchannel.hostport

ioloop.IOLoop.current().start()
