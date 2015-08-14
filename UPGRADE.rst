Version Upgrade Guide
=====================

Migrating to a version of TChannel with breaking changes? This guide documents
what broke and how to safely migrate to newer versions.

From 0.15 to 0.16
-----------------

- Remove ``retry_delay`` option from ``tchannel.tornado.peer.PeerClientOperation.send``
  method.

  Before: ``tchannel.request.send(retry_delay=300)``

  After: no more ``retry_delay`` in  ``tchannel.request.send()``

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

