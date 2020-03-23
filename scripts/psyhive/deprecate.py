"""Tools for deprecating code.

The deprecation has no effect outside dev mode, although its use is logged in
kibana. In dev mode, raises an error if the function is called (in the case
of a function deprecation) or if the code is executed (in the case of a basic
deprecation).

Deprecated functions should be removed from the codebase 100 days after the
deprecation.

Only public functions should be deprecated.
"""

import functools
import time

from psyhive.tools import track_usage
from psyhive.utils import dev_mode, get_time_f


class _DeprecationError(Exception):
    """Raised if dev mode if a deprecated function is called."""


def _read_tag(tag):
    """Read age/notes from deprecation tag.

    Args:
        tag (str): deprecation tag

    Returns:
        (tuple): deprecation age in days, deprecation note
    """
    _tokens = tag.split()
    _date, _note = _tokens[0], ' '.join(_tokens[1:])
    _mtime = get_time_f(time.strptime(_date, '%d/%m/%y'))
    _age_days = (time.time() - _mtime)/(60*60*24)

    return _age_days, _note


@track_usage
def apply_deprecation(tag):
    """Apply a deprecation at this point in the code.

    This prevents the code from running in dev mode.

    Args:
        tag (str): deprecation tag
    """
    _age_days, _note = _read_tag(tag)
    print 'APPLYING DEPRECATION {} ({:d} days old) dev={:d}'.format(
        _note, int(_age_days), dev_mode())

    if dev_mode():
        raise _DeprecationError


def deprecate_func(tag):
    """Build a decorator to apply a deprecation to the given function.

    Args:
        tag (str): deprecation tag

    Returns:
        (dec): deprecation decorator
    """
    _read_tag(tag)  # Check tag

    def _func_deprecator(func):

        @functools.wraps(func)
        def _deprecated_func(*args, **kwargs):

            apply_deprecation(tag)
            return func(*args, **kwargs)

        return _deprecated_func

    return _func_deprecator
