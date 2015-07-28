from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from abc import ABCMeta, abstractproperty, abstractmethod


class Formatter(object):
    __metaclass__ = ABCMeta

    def __init__(self, tchannel):
        self.tchannel = tchannel

    @abstractproperty
    def name(self):
        pass

    @abstractmethod
    def call(self):
        pass

    @abstractmethod
    def stream(self):
        pass
