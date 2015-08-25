Version Upgrade Guide
=====================

Migrating to a version of TChannel with breaking changes? This guide documents
what broke and how to safely migrate to newer versions.

From 0.15 to 0.16
-----------------

- ``tchannel.TChannel.register`` no longer mimicks
  ``tchannel.tornado.TChannel.register``, instead it exposes the new server API
  like so:

  Before:

  .. code:: python

      from tchannel.tornado import TChannel

      tchannel = TChannel('my-service-name')

      @tchannel.register('endpoint', 'json')
      def endpoint(request, response, proxy):
          response.write({'resp': 'body'})


  After:

  .. code:: python

      from tchannel import TChannel

      tchannel = TChannel('my-service-name')

      @tchannel.json.register
      def endpoint(request):
          return {'resp': 'body'}

          # Or, if you need to return headers with your response:
          from tchannel import Response
          return Response({'resp': 'body'}, {'header': 'foo'})

- ``from tchannel.tornado import TChannel`` is deprecated.

- Removed ``retry_delay`` option from
  ``tchannel.tornado.peer.PeerClientOperation.send`` method.

  Before: ``tchannel.tornado.TChannel.request.send(retry_delay=300)``

  After: no more ``retry_delay`` in  ``tchannel.tornado.TChannel.request.send()``

- If you were catching ``ProtocolError`` you will need to catch a more specific
  type, such as ``TimeoutError``, ``BadRequestError``, ``NetworkError``,
  ``UnhealthyError``, or ``UnexpectedError``.

- If you were catching ``AdvertiseError``, it has been replaced by
  ``TimeoutError``.

- If you were catching ``BadRequest``, it may have been masking checksum errors
  and fatal streaming errors. These are now raised as ``FatalProtocolError``,
  but in practice should not need to be handled when interacting with a
  well-behaved TChannel implementation.

- ``TChannelApplicationError`` was unused and removed.

- Three error types have been introduced to simplify retry handling:
  - ``NotRetryableError`` (for requests should never be retried),
  - ``RetryableError`` (for requests that are always safe to retry), and
  - ``MaybeRetryableError`` (for requests that are safe to retry on idempotent
    endpoints).


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

