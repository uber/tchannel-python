from __future__ import absolute_import

from tornado import gen

from ..response import response_from_mixed


@gen.coroutine
def handle(tchannel, request):
    """Test util function to have tchannel instance to take predefined request
    object.

    .. code-block:: python
        tchannel = TChannel('example')

        @tchannel.raw.register
        @gen.coroutine
        def testString(request):
            return Response('resp', headers={'resp': 'header'})

        request = Request(
            body="body",
            headers={},
            transport={},
            endpoint="endpoint",
        )

        response = yield handle(tchannel, request)

    :param tchannel:
        An instance of ``tchannel.TChannel`` that has registered endpoints.

    :param request:
        An instance of ``tchannel.Request``.

    :return
        Return the ``tchannel.Response`` from User's endpoint.
    """
    resp = yield gen.maybe_future(tchannel._dep_tchannel._handler.get_endpoint(
        request.endpoint
    ).endpoint(request))

    raise gen.Return(response_from_mixed(resp))
