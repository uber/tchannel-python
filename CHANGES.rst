Changes by Version
==================

0.21.5 (unreleased)
-------------------

- Tornado 4.2 was listed as a requirement but this was corrected to be 4.3
  which introduced the locks module.


0.21.4 (2016-02-15)
-------------------

- Fixed noisy logging of late responses for requests that timed out locally.


0.21.3 (2016-01-22)
-------------------

- Attempting to register endpoints against a synchronous TChannel is now a no-op instead of a crash.


0.21.2 (2016-01-05)
-------------------

- The synchronous client will no longer start a thread when the ``TChannel``
  instance is initialized. This resolves an issue where an application could
  hang indefinitely if it instantiated a synchronous ``TChannel`` at import
  time.


0.21.1 (2015-12-29)
-------------------

- Fixed a bug in Zipkin instrumentation that would cause CPU spikes due to an
  infinite loop during downstream requests.


0.21.0 (2015-12-10)
-------------------

- Add support for zipkin trace sampling.
- ``tchannel.TChannel.FALLBACK`` may now be used to register fallback endpoints
  which are called for requests with unrecognized endpoints. For more
  information, see :ref:`fallback-endpoint`
- Expose ``timeout`` and ``service`` attributes on ``Request`` objects inside
  endpoint handlers.
- Disable the retry for all zipkin trace submit.
- Fix Thrift service inheritance bug which caused parent methods to not be
  propagated to child services.
- VCR recording should not fail if the destination directory for the cassette
  does not exist.
- Fix bug which incorrectly encoded JSON arg scheme headers in the incorrect
  format.
- Add support for ``rd`` transport header.
- **BREAKING** - Support unit testing endpoints by calling the handler
  functions directly. This is enabled by changing ``tchannel.thrift.register``
  to return the registered function unmodified. See Upgrade Guide for more
  details.


0.20.2 (2015-11-25)
-------------------

- Lower the log level for Hyperbahn advertisement failures that can be retried.
- Include the full stack trace when Hyperbahn advertisement failures are logged.
- Include the error message for unexpected server side failures in the error returned to the client.


0.20.1 (2015-11-12)
-------------------

- Fix bug which prevented requests from being retried if the candidate
  connection was previously terminated.


0.20.0 (2015-11-10)
-------------------

- Support thriftrw 1.0.
- Drop explicit dependency on the ``futures`` library.


0.19.0 (2015-11-06)
-------------------

- Add tchannel version & language information into init message header when
  initialize connections between TChannel instances.


0.18.3 (2015-11-03)
-------------------

- Reduced Hyperbahn advertisement per-request timeout to 2 seconds.
- Removed an unncessary exception log for connection failures.


0.18.2 (2015-10-28)
-------------------

- Reduced Hyperbahn advertisement failures to warnings.


0.18.1 (2015-10-28)
-------------------

- Improved performance of peer selection logic.
- Fixed a bug which caused the message ID and tracing for incoming error frames
  to be ignored.
- Prefer using incoming connections on peers instead of outgoing connections.


0.18.0 (2015-10-20)
-------------------

- Deprecated warnings will now sound for ``tchannel.thrift.client_for``,
  ``tchannel.thrift_request_builder``, and ``tchannel.tornado.TChannel`` - these
  APIs will be removed soon - be sure to move to ``tchannel.thrift.load`` in
  conjunction with ``tchannel.TChannel``.
- Added singleton facility for maintaining a single TChannel instance per thread.
  See ``tchannel.singleton.TChannel``, ``tchannel.sync.singleton.TChannel``, or check
  the guide for an example how of how to use. Note this feature is optional.
- Added Thrift support to ``tcurl.py`` and re-worked the script's arguments.
- Specify which request components to match on with VCR, for example, 'header',
  'body', etc. See ``tchannel.testing.vcr.use_cassette``.
- Removed ``tchannel.testing.data`` module.
- Changed minimum required version of Tornado to 4.2.
- ``tchannel.tornado.TChannel.close`` is no longer a coroutine.
- **BREAKING** - headers for JSON handlers are not longer JSON blobs but are
  instead maps of strings to strings. This mirrors behavior for Thrift
  handlers.
- Fixed bug that caused server to continue listening for incoming connections
  despite closing the channel.
- Explicit destinations for ``ThriftArgScheme`` may now be specified on a
  per-request basis by using the ``hostport`` keyword argument.
- Only listen on IPv4, until official IPv6 support arrives.


0.17.11 (2015-10-19)
--------------------

- Fix a bug that caused ``after_send_error`` event to never be fired.
- Request tracing information is now propagated to error responses.


0.17.10 (2015-10-16)
--------------------

- Support thriftrw 0.5.


0.17.9 (2015-10-15)
-------------------

- Fix default timeout incorrectly set to 16 minutes, now 30 seconds.


0.17.8 (2015-10-14)
-------------------

- Revert timeout changes from 0.17.6 due to client incompatibilities.


0.17.7 (2015-10-14)
-------------------

- Network failures while connecting to randomly selected hosts should be
  retried with other hosts.


0.17.6 (2015-10-14)
-------------------

- Fixed an issue where timeouts were being incorrectly converted to seconds.


0.17.5 (2015-10-12)
-------------------

- Set default checksum to ``CRC32C``.


0.17.4 (2015-10-12)
-------------------

- Updated ``vcr`` to use ``thriftrw``-generated code. This should resolve some
  unicode errors during testing with ``vcr``.


0.17.3 (2015-10-09)
-------------------

- Fixed uses of ``add_done_callback`` that should have been ``add_future``.
  This was preventing propper request/response interleaving.
- Added support for ``thriftrw`` 0.4.


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


0.16.10 (2015-10-15)
--------------------

- Fix default timeout incorrectly set to 16 minutes, now 30 seconds.


0.16.9 (2015-10-15)
-------------------

- Network failures while connecting to randomly selected hosts should be
  retried with other hosts.


0.16.8 (2015-10-14)
-------------------

- Revert timeout changes from 0.16.7 due to client incompatibilities.


0.16.7 (2015-10-14)
-------------------

- Fixed an issue where timeouts were being incorrectly converted to seconds.


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
