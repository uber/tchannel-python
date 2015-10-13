from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import functools
import warnings


def deprecate(message):
    """Loudly prints warning."""
    warnings.simplefilter('default')
    warnings.warn(message, category=DeprecationWarning)
    warnings.resetwarnings()


def deprecated(message):
    """Warn every time a fn is called."""
    def decorator(fn):
        @functools.wraps(fn)
        def new_fn(*args, **kwargs):
            deprecate(message)
            return fn(*args, **kwargs)
        return new_fn
    return decorator
