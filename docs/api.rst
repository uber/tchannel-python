API Documentation
=================


TChannel
--------

.. autoclass:: tchannel.TChannel
    :special-members: __init__
    :members:

.. autoclass:: tchannel.singleton.TChannel
    :members:

.. autoclass:: tchannel.Request
    :members:

.. autoclass:: tchannel.Response
    :members:

.. automodule:: tchannel.context
    :members:


Serialization Schemes
---------------------

Thrift
~~~~~~

.. autoclass:: tchannel.schemes.ThriftArgScheme
    :members: __call__, register

.. autofunction:: tchannel.thrift.load

.. autofunction:: tchannel.thrift_request_builder

JSON
~~~~

.. autoclass:: tchannel.schemes.JsonArgScheme
    :members: __call__, register

Raw
~~~
.. autoclass:: tchannel.schemes.RawArgScheme
    :members: __call__, register


Exception Handling
------------------

Errors
~~~~~~
.. automodule:: tchannel.errors
    :members:
    :show-inheritance:

Retry Behavior
~~~~~~~~~~~~~~

These values can be passed as the ``retry_on`` behavior to
:py:meth:`tchannel.TChannel.call`.

.. automodule:: tchannel.retry
    :members:


Synchronous Client
------------------

.. autoclass:: tchannel.sync.TChannel
    :inherited-members:
    :members:

.. autoclass:: tchannel.sync.singleton.TChannel
    :inherited-members:
    :members:


Testing
-------

.. automodule:: tchannel.testing.vcr

..
    This automodule directive intentionally doesn't include :members: because
    the module documentation for it explicitly calls out members that should be
    documented.

