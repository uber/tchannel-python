import json
import logging

import crossdock.server.api as api
import opentracing
import tornado.escape
import tornado.gen
import tornado.httpclient
import tornado.ioloop
import tornado.web
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from opentracing_instrumentation import get_current_span
from tchannel import thrift, Response, TChannel

DEFAULT_CLIENT_PORT = 8080
DEFAULT_SERVER_PORT = 8081

idl_path = 'crossdock/server/simple-service.thrift'
thrift_services = {}


def serve():
    """main entry point"""
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info('Python Tornado Crossdock Server Starting ...')

    tracer = Tracer(
        service_name='python',
        reporter=NullReporter(),
        sampler=ConstSampler(decision=True))
    opentracing.tracer = tracer

    tchannel = TChannel(name='python', hostport=':%d' % DEFAULT_SERVER_PORT,
                        trace=True)
    register_tchannel_handlers(tchannel=tchannel)
    tchannel.listen()

    app = tornado.web.Application(debug=True)
    register_http_handlers(app)
    app.listen(DEFAULT_CLIENT_PORT)

    tornado.ioloop.IOLoop.current().start()


def register_http_handlers(app):
    app.add_handlers(".*$", [
        (r"/", HttpHandler, )
    ])


def get_thrift_service(service_name):
    if service_name in thrift_services:
        return thrift_services[service_name]
    thrift_service = thrift.load(path=idl_path, service=service_name)
    thrift_services[service_name] = thrift_service
    return thrift_service


def register_tchannel_handlers(tchannel):
    @tchannel.json.register('trace')
    @tornado.gen.coroutine
    def json_trace_handler(request):
        res = yield _process_request(request.body)
        raise tornado.gen.Return(Response(body=res))

    thrift_service = get_thrift_service(service_name='python')

    @tchannel.thrift.register(thrift_service.SimpleService, method='Call')
    @tornado.gen.coroutine
    def thrift_trace_handler(request):
        logging.info('Received thrift request: %s', request.body.arg.s2)
        req = json.loads(request.body.arg.s2)
        res = yield _process_request(req)
        data = thrift_service.Data(b1=False, i3=0, s2=json.dumps(res))
        raise tornado.gen.Return(data)

    @tornado.gen.coroutine
    def _process_request(req_dict):
        req = api.request_from_dict(req_dict)
        span = observe_span()
        downstream = yield call_downstream(
            tchannel=tchannel,
            target=req.downstream)
        res = api.Response(span=span, downstream=downstream)
        raise tornado.gen.Return(api.namedtuple_to_dict(res))

    logging.info('TChannel handlers registered ...')


def observe_span():
    span = get_current_span()
    logging.info('Observed span: %s', span)
    if span is None:
        return api.ObservedSpan(traceId='missing', sampled=False, baggage='')
    return api.ObservedSpan(
        traceId="%x" % span.trace_id,
        sampled=span.is_sampled(),
        baggage=span.get_baggage_item(api.BAGGAGE_KEY),
    )


@tornado.gen.coroutine
def call_downstream(tchannel, target):
    if not target:
        raise tornado.gen.Return(None)

    req = api.Request(serverRole=target.serverRole,
                      downstream=target.downstream)
    req = api.namedtuple_to_dict(req)

    if target.encoding == 'json':
        response = yield tchannel.json(
            service=target.serviceName,
            endpoint='trace',
            hostport=target.hostPort,
            body=req,
        )
        res = api.response_from_dict(response.body)
    elif target.encoding == 'thrift':
        thrift_service = get_thrift_service(service_name=target.serviceName)
        data = thrift_service.Data(b1=False, i3=0, s2=json.dumps(req))
        response = tchannel.thrift(
            thrift_service.SimpleService.Call(data),
            hostport=target.hostPort,
        )
        response = yield response
        body = response.body
        res = api.response_from_dict(json.loads(body.s2))
    else:
        raise ValueError(target.encoding)
    raise tornado.gen.Return(res)


# noinspection PyAbstractClass
class HttpHandler(tornado.web.RequestHandler):
    """
    Crossdock client is implemented in Go, so we only need to support
    HTTP HEAD request used by crossdock as a health check at port 8080.
    """
    def __init__(self, application, request, **kwargs):
        super(HttpHandler, self).__init__(application, request, **kwargs)

    def head(self):
        """This is used by crossdock as a health check"""
        pass


if __name__ == "__main__":
    serve()
