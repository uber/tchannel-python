API Documentation
=================


TChannel
--------

.. autoclass:: tchannel.TChannel
    :members:

.. autoclass:: tchannel.schemes.RawArgScheme
    :members:

.. autoclass:: tchannel.schemes.JsonArgScheme
    :members:

.. autoclass:: tchannel.schemes.ThriftArgScheme
    :members:

.. autoclass:: tchannel.tornado.RequestDispatcher
    :members:

.. autoclass:: tchannel.tornado.Request
    :members:

.. autoclass:: tchannel.tornado.Response
    :members:


Exceptions
----------

.. automodule:: tchannel.errors
    :members:


Thrift
------

.. automodule:: tchannel.thrift.client
    :members:


Synchronous Client
------------------

.. automodule:: tchannel.sync.client
    :members:

.. automodule:: tchannel.sync.thrift
    :members:


Testing
-------

.. automodule:: tchannel.testing.vcr

..
    This automodule directive intentionally doesn't include :members: because
    the module documentation for it explicitly calls out members that should be
    documented.
