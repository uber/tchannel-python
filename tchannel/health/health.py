from __future__ import absolute_import

from .thrift.ttypes import HealthStatus


def health(request):
    return HealthStatus(ok=True)
