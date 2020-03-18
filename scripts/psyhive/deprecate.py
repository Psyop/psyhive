"""Tools for deprecating code.

Deprecated code should error if executed in dev_mode.

Usage of deprecated code should be tracked using kibana.

Deprecated functions should be removed from the codebase 100 days after the 
deprecation.

Only public functions should be deprecated.
"""

import time

from psyhive.tools import track_usage
from psyhive.utils import dev_mode, get_time_f, FileError


class _DeprecationError(Exception):
    pass


@track_usage
def apply_deprecation(tag):

    _tokens = tag.split()
    _date, _note = _tokens[0], ' '.join(_tokens[1:])
    _mtime = get_time_f(time.strptime(_date, '%d/%m/%y'))
    _age_days = (time.time() - _mtime)/(60*60*24)
    print 'APPLYING DEPRECATION {} ({:d} days old) dev={:d}'.format(
        _note, int(_age_days), dev_mode())

    if dev_mode():
        raise _DeprecationError


def deprecate_func(tag):

    def _func_deprecator(func):

        def _deprecated_func(*args, **kwargs):

            apply_deprecation(tag)
            return func(*args, **kwargs)

        return _deprecated_func

    return _func_deprecator
