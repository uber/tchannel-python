from tornado import gen, ioloop

from tchannel import TChannel, from_thrift_module

from tests.data.generated.ThriftTest import ThriftTest


tchannel = TChannel('thrift-client')

service = '10.32.160.131:52294'
thrift_client = from_thrift_module(service, ThriftTest)


@gen.coroutine
def make_request():

    resp = yield tchannel.thrift(
        request=thrift_client.testString(thing="holler"),

        # TODO bug, you have to have headers :P
        headers={'wtf': 'dude'}
    )

    raise gen.Return(resp)


io_loop = ioloop.IOLoop.current()

resp = io_loop.run_sync(make_request)


# TODO impl __repr__
print resp.body

# TODO wtf tests have headers...
print resp.headers

print resp.transport
