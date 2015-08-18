Version Upgrade Guide
=====================

Migrating to a version of TChannel with breaking changes? This guide documents
what broke and how to safely migrate to newer versions.

From 0.15 to 0.16
-----------------

- ``tchannel.TChannel.register`` no longer mimicks ``tchannel.tornado.TChannel.register``,
  instead it exposes the new server API like so:

  Before:

  .. code:: python

      from tchannel import TChannel

      @tchannel.register('endpoint', 'json')
      def endpoint(request, response, proxy):
          response.write({'resp': 'body'})


  After:

  .. code:: python

      from tchannel import TChannel, Response

      @tchannel.json.register
      def endpoint(request):
          return Response({'resp': 'body'})


- Remove ``retry_delay`` option from ``tchannel.tornado.peer.PeerClientOperation.send``
  method.

  Before: ``tchannel.tornado.TChannel.request.send(retry_delay=300)``

  After: no more ``retry_delay`` in  ``tchannel.tornado.TChannel.request.send()``

From 0.14 to 0.15
-----------------

- No breaking changes.

From 0.13 to 0.14
-----------------

- No breaking changes.

From 0.12 to 0.13
-----------------

- No breaking changes.


From 0.11 to 0.12
-----------------

- Removed ``print_arg``. Use ``request.get_body()`` instead.

From 0.10 to 0.11
-----------------

- Renamed ``tchannel.tornado.TChannel.advertise`` argument ``router`` to ``routers``.
  Since this is a required arg and the first positional arg, only clients who are
  using as kwarg will break.

  Before: ``tchannel.advertise(router=['localhost:21300'])``

  After: ``tchannel.advertise(routers=['localhost:21300'])``

