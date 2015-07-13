from __future__ import absolute_import


from tchannel.thrift.util import get_service_methods


def test_get_service_methods():

    class Iface(object):

        def __init__(self):
            pass

        def hello(self):
            pass

        def world(self, foo):
            pass

    assert set(['hello', 'world']) == get_service_methods(Iface)
