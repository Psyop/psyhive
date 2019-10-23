"""Tools for managing the check heart loop breaker tool."""

import os
import time

_INITIATED = False
_LAST_CHECK = None


def check_heart():
    """Check the heart file exists.

    This is an empty file in the user's home area. The tool is used to
    prevent maya from being stuck in an infinite/slow loop - the check
    is placed in an iteration and the user can delete the file to break
    the loop.

    Raises:
        (RuntimeError): if the heart file is missing
    """

    from psyhive.utils.path import touch, abs_path

    global _INITIATED, _LAST_CHECK

    _heart = abs_path('~/.heart')

    # Make sure heart exists
    if not _INITIATED:
        touch(_heart)
        _INITIATED = True

    # Only check once a second
    if _LAST_CHECK and time.time() - _LAST_CHECK < 1.0:
        return

    if not os.path.exists(_heart):
        touch(_heart)
        raise RuntimeError("Missing heart")

    _LAST_CHECK = time.time()
