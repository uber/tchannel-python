Version Upgrade Guide
=====================

Migrating to a version of TChannel with breaking changes? This guide documents
what broke and how to safely migrate to newer versions.

From 0.10 to 0.11
-----------------

- Renamed :python:`tchannel.tornado.TChannel.advertise` argument `router` to `routers`.
  Since this is a required arg and the first positional arg, only clients who are
  using as kwarg will break.

  Before: :python:`tchannel.advertise(router=['localhost:21300'])`
  After: :python:`tchannel.advertise(routers=['localhost:21300'])`


.. role:: python(code)
   :language: python
