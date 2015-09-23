Changes by Version
==================

0.17.3 (unreleased)
-------------------

- Add ``TChannel.stop()`` method to gracefully shutdown TChannel server.


0.17.2 (2015-09-18)
-------------------

- VCR no longer matches on hostport to better support ephemeral ports.
- Fixed a bug with thriftrw where registering an endpoint twice could fail.


0.17.1 (2015-09-17)
-------------------

- Made "service" optional for ``thrift.load()``. The first argument should be a
  path, but backwards compatibility is provided for 0.17.0.


0.17.0 (2015-09-14)
-------------------

- It is now possible to load Thrift IDL files directly with
  ``tchannel.thrift.load``. This means that the code generation step using the
  Apache Thrift compiler can be skipped entirely. Check the API documentation
  for more details.
- Accept host file in advertise: ``TChannel.advertise()`` now accepts
  a parameter, ``router_file`` that contains a JSON stringified format
  of the router list.
- Add ``TChannel.is_listening`` method to return whether the tchannel instance
  is listening or not.


0.16.6 (2015-09-14)
-------------------

- Fixed a bug where Zipkin traces were not being propagated correctly in
  services using the ``tchannel.TChannel`` API.


0.16.5 (2015-09-09)
-------------------

- Actually fix status code being unset in responses when using the Thrift
  scheme.
- Fix request TTLs not being propagated over the wire.


0.16.4 (2015-09-09)
-------------------

- Fix bug where status code was not being set correctly on call responses for
  application errors when using the Thrift scheme.


0.16.3 (2015-09-09)
-------------------

- Make ``TChannel.listen`` thread-safe and idempotent.


0.16.2 (2015-09-04)
-------------------

- Fix `retry_limit` in `TChannel.call` not allowing 0 retries.


0.16.1 (2015-08-27)
-------------------

- Fixed a bug where the 'not found' handler would incorrectly return
  serialization mismatch errors..
- Fixed a bug which prevented VCR support from working with the sync client.
- Fixed a bug in VCR that prevented it from recording requests made by the sync
  client, and requests made with ``hostport=None``.
- Made ``client_for`` compatible with ``tchannel.TChannel``.
- Brought back ``tchannel.sync.client_for`` for backwards compatibility.


0.16.0 (2015-08-25)
-------------------

- Introduced new server API through methods
  ``tchannel.TChannel.thrift.register``, ``tchannel.TChannel.json.register``,
  and ``tchannel.TChannel.raw.register`` - when these methods are used,
  endpoints are passed a ``tchannel.Request`` object, and are expected to
  return a ``tchannel.Response`` object or just a response body. The deprecated
  ``tchannel.tornado.TChannel.register`` continues to function how it did
  before. Note the breaking change to the top-level TChannel on the next line.
- Fixed a crash that would occur when forking with an unitialized ``TChannel``
  instance.
- Add ``hooks`` property in the ``tchannel.TChannel`` class.
- **BREAKING** - ``tchannel.TChannel.register`` no longer has the same
  functionality as ``tchannel.tornado.TChannel.register``, instead it exposes
  the new server API. See the upgrade guide for details.
- **BREAKING** - remove ``retry_delay`` option in the ``tchannel.tornado.send``
  method.
- **BREAKING** - error types have been reworked significantly. In particular,
  the all-encompassing ``ProtocolError`` has been replaced with more
  granualar/actionable exceptions. See the upgrade guide for more info.
- **BREAKING** - Remove third ``proxy`` argument from the server handler
  interface.
- **BREAKING** - ``ZipkinTraceHook`` is not longer registered by default.
- **BREAKING** - ``tchannel.sync.client.TChannelSyncClient`` replaced with
  ``tchannel.sync.TChannel``.


0.15.2 (2015-08-07)
-------------------

- Raise informative and obvious ``ValueError`` when anything
  but a map[string]string is passed as headers to the ``TChannel.thrift`` method.
- First param, request, in ``tchannel.thrift`` method is required.


0.15.1 (2015-08-07)
-------------------

- Raise ``tchannel.errors.ValueExpectedError`` when calling a non-void Thrift procedure
  that returns no value.


0.15.0 (2015-08-06)
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
