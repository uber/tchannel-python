Changelog
=========


0.15.0 (unreleased)
-------------------

- Introduced new top level ``tchannel.TChannel`` object, with new request methods
  ``call``, ``raw``, ``json``, and ``thrift``. This will eventually replace the
  akward ``request`` / ``send`` calling pattern.
- Introduced ``tchannel.thrift_request_builder`` function for creating a
  request builder to be used with the ``tchannel.TChannel.thrift`` function.
- Introduced new simplified examples under the ``examples/simple`` directory, moved
  the Guide's examples to ``examples/guide``, and deleted the remaining examples.
- Added ThriftTest.thrift and generated Thrift code to ``tchannel.testing.data`` for
  use with examples and playing around with TChannel.
- Fix JSON arg2 (headers) being returned a string instead of a dict.


0.14.0 (2015-08-03)
-------------------

- Implement VCR functionality for outgoing requests. Check the documentation
  for ``tchannel.testing.vcr`` for details.
- Add support for specifying fallback handlers via ``TChannel.register`` by
  specifying ``TChannel.fallback`` as the endpoint.
- Fix bug in ``Response`` where ``code`` expected an object instead of an
  integer.
- Fix bug in ``Peer.close`` where a future was expected instead of ``None``.


0.13.0 (2015-07-23)
-------------------

- Add support for specifying transport headers for Thrift clients.
- Always pass ``shardKey`` for TCollector tracing calls. This fixes Zipkin tracing for Thrift clients.


0.12.0 (2015-07-20)
-------------------

- Add ``TChannel.is_listening()`` to determine if ``listen`` has been called.
- Calling ``TChannel.listen()`` more than once raises a ``tchannel.errors.AlreadyListeningError``.
- ``TChannel.advertise()`` will now automatically start listening for connections
  if ``listen()`` has not already been called.
- Use ``threadloop==0.4``.
- Removed ``print_arg``.


0.11.2 (2015-07-20)
-------------------

- Fix sync client's advertise - needed to call listen in thread.


0.11.1 (2015-07-17)
-------------------

- Fix sync client using ``0.0.0.0`` host which gets rejected by Hyperbahn during advertise.


0.11.0 (2015-07-17)
-------------------

- Added advertise support to sync client in ``tchannel.sync.TChannelSyncClient.advertise``.
- **BREAKING** - renamed ``router`` argument to ``routers`` in ``tchannel.tornado.TChannel.advertise``.


0.10.3 (2015-07-13)
-------------------

- Support PyPy 2.
- Fix bugs in ``TChannel.advertise``.


0.10.2 (2015-07-13)
-------------------

- Made ``TChannel.advertise`` retry on all exceptions.


0.10.1 (2015-07-10)
-------------------

- Previous release was broken with older versions of pip.


0.10.0 (2015-07-10)
-------------------

- Add exponential backoff to ``TChannel.advertise``.
- Make transport metadata available under ``request.transport`` on the
  server-side.


0.9.1 (2015-07-09)
------------------

- Use threadloop 0.3.* to fix main thread not exiting when ``tchannel.sync.TChannelSyncClient`` is used.


0.9.0 (2015-07-07)
------------------

- Allow custom handlers for unrecognized endpoints.
- Released ``tchannel.sync.TChannelSyncClient`` and ``tchannel.sync.thrift.client_for``.


0.8.5 (2015-06-30)
------------------

- Add port parameter for ``TChannel.listen``.


0.8.4 (2015-06-17)
------------------

- Fix bug where False and False-like values were being treated as None in
  Thrift servers.


0.8.3 (2015-06-15)
------------------

- Add ``as`` attribute to the response header.


0.8.2 (2015-06-11)
------------------

- Fix callable ``traceflag`` being propagated to the serializer.
- Fix circular imports.
- Fix ``TimeoutError`` retry logic.


0.8.1 (2015-06-10)
------------------

- Initial release.
