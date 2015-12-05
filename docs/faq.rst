FAQ
===

.. _fallback-endpoint:

Can I register an endpoint that accepts all requests?
-----------------------------------------------------

The fallback endpoint is the endpoint called when an unrecognized request is
received. By default, the fallback endpoint simply returns a
``BadRequestError`` to the caller. This behavior may be overriden by
registering a raw endpoint with ``TChannel.FALLBACK``.

.. code-block:: python

    from tchannel import TChannel

    server = TChannel(name='myservice')

    @server.register('raw', TChannel.FALLBACK)
    def handler(request):
        # ...

This may be used to implement a TChannel server that can handle requests to all
endpoints. Note that for the fallback endpoint, you have access to the raw
bytes of the headers and the body. These must be serialized/deserialized
manually.
