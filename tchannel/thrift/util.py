from __future__ import absolute_import


import inspect


def get_service_methods(iface):
    """Get a list of methods defined in the interface for a Thrift service.

    :param iface:
        The Thrift-generated Iface class defining the interface for the
        service.
    :returns:
        A set containing names of the methods defined for the service.
    """
    methods = inspect.getmembers(iface, predicate=inspect.ismethod)

    return set(
        name for (name, method) in methods if not name.startswith('__')
    )
