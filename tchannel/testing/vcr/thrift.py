# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import

from thrift.Thrift import TType
from thrift.protocol.TBase import TBase

from .exceptions import VCRError


def to_native(ttype, data, extra=None):
    """Converts types into native classes and objects.

    :param ttype:
        Type of value to construct
    :param data:
        Raw Thrift value. For primitive types, this is usually unchanged. For
        structs it's a dictionary.
    :param extra:
        Extra information about the ttype.
    """
    if TType.LIST == ttype:
        return [to_native(extra[0], x, extra[1]) for x in data]
    elif TType.MAP == ttype:
        return {
            to_native(extra[0], k, extra[1]): to_native(extra[2], v, extra[3])
            for k, v in data.items()
        }
    elif TType.SET == ttype:
        return set([to_native(extra[0], x, extra[1]) for x in data])
    elif TType.STRUCT == ttype:
        cls = extra[0]
        spec = extra[1]
        kwargs = {}
        for entry in spec:
            if entry is None:
                continue
            name = entry[2]
            if name in data:
                kwargs[name] = to_native(entry[1], data[name], entry[3])
        return cls(**kwargs)
    else:
        return data


def to_primitive(ttype, value, extra=None):
    """Convert arbitrary Thrift values into serializable primitives.

    :param ttype:
        Type of the value being converted
    :param value:
        Value to convert
    :param extra:
        Extra information about the type
    """
    if TType.LIST == ttype:
        return [to_primitive(extra[0], x, extra[1]) for x in value]
    elif TType.MAP == ttype:
        return {
            to_primitive(extra[0], k, extra[1]):
                to_primitive(extra[2], v, extra[3])
            for k, v in value.items()
        }
    elif TType.SET == ttype:
        return [to_primitive(extra[0], x, extra[1]) for x in value]
    elif TType.STRUCT == ttype:
        spec = extra[1]
        data = {}
        for entry in spec:
            if entry is None:
                continue
            name = entry[2]
            attr = getattr(value, name)
            if attr is not None:
                data[name] = to_primitive(entry[1], attr, entry[3])
        return data
    else:
        return value


def enum_to_name(cls, value):
    return cls._VALUES_TO_NAMES[value]


def enum_values(cls):
    return cls._NAMES_TO_VALUES.values()


class VCRThriftMeta(type):

    def __new__(cls, name, bases, dct):
        if '_VALUES_TO_NAMES' in dct:
            # Provide a way to convert an enum value into its name.
            dct['to_name'] = classmethod(enum_to_name)
            dct['values'] = classmethod(enum_values)

        return type.__new__(cls, name, bases, dct)


class VCRThriftBase(TBase, object):
    """Base class for generated Thrift types.

    Adds the following:

    - ``to_primitive`` method to convert objects into serializable primitives.
    - ``to_native`` class method to construct objects of the class from
        primitives.
    - Readable ``__str__`` and ``__repr__`` methods.
    - For enums, a ``to_name`` class method that maps enum values to the enum
      value name, and a ``values`` method that returns a list of values
      defined for the enum.
    """

    __metaclass__ = VCRThriftMeta

    # TODO do we want to create copies of these types with manual mappers
    # instead?

    @classmethod
    def to_native(cls, data):
        return to_native(TType.STRUCT, data, (cls, cls.thrift_spec))

    def to_primitive(self):
        return to_primitive(
            TType.STRUCT, self, (self.__class__, self.thrift_spec)
        )

    # A more useful __str__ implementation

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.to_primitive()))

    __repr__ = __str__


class VCRThriftError(VCRThriftBase, VCRError):
    "Base class for generated exceptions."""


__all__ = ['VCRThriftBase', 'VCRThriftError']
