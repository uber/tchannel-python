API Documentation
=================


TChannel
--------

.. autoclass:: tchannel.TChannel
    :members:

.. autoclass:: tchannel.Request
    :members:

.. autoclass:: tchannel.Response

.. autoclass:: tchannel.schemes.RawArgScheme
    :members:

.. autoclass:: tchannel.schemes.JsonArgScheme
    :members:

.. autoclass:: tchannel.schemes.ThriftArgScheme
    :members:

.. autofunction:: tchannel.thrift_request_builder


Exceptions
----------

.. automodule:: tchannel.errors
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


Deprecated
----------

.. autoclass:: tchannel.tornado.TChannel

.. autoclass:: tchannel.tornado.Request
    :members:

.. autoclass:: tchannel.tornado.Response
    :members:

.. automodule:: tchannel.thrift.client
    :members:


