from __future__ import absolute_import

import yaml

try:
    # Prefer LibYAML-based parser and serializer
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def load(s):
    return yaml.load(s, Loader=Loader)


def dump(d):
    return yaml.dump(d, Dumper=Dumper, default_flow_style=False)


__all__ = ['load', 'dump']
