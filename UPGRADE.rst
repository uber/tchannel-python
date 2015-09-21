.. _upgrade guide:

Upgrade Guide
=============

Migrating to a version of TChannel with breaking changes? This guide documents
what broke and how to safely migrate to newer versions.

From 0.16 to 0.17
-----------------

- No breaking changes.

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

- ``TChannelSyncClient`` has been replaced with ``tchannel.sync.TChannel``.
  This new synchronous client has been significantly re-worked to more closely
  match the asynchronous ``TChannel`` API. ``tchannel.sync.thrift.client_for``
  has been removed and ``tchannel.thrift_request_builder`` should be used
  instead (``tchannel.thrift.client_for`` still exists for backwards
  compatibility but is not recommended). This new API allows specifying
  headers, timeouts, and retry behavior with Thrift requests.

  Before:

  .. code:: python

      from tchannel.sync import TChannelSyncClient
      from tchannel.sync.thrift import client_for

      from generated.thrift.code import MyThriftService

      tchannel_thrift_client = client_for('foo', MyThriftService)

      tchannel = TChannelSyncClient(name='bar')

      future = tchannel_thrift_client.someMethod(...)

      result = future.result()


  After:

  .. code:: python

      from tchannel import thrift_request_builder
      from tchannel.sync import TChannel
      from tchannel.retry import CONNECTION_ERROR_AND_TIMEOUT

      from generated.thrift.code import MyThriftService

      tchannel_thrift_client = thrift_request_builder(
          service='foo',
          thrift_module=MyThriftService,
      )

      tchannel = TChannel(name='bar')

      future = tchannel.thrift(
          tchannel_thrift_client.someMethod(...)
          headers={'foo': 'bar'},
          retry_on=CONNECTION_ERROR_AND_TIMEOUT,
          timeout=1000,
      )

      result = future.result()

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

