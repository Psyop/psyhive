"""Tools for managing the check heart loop breaker tool."""

import time

from .path import File, abs_path

HEART = File(abs_path('~/.heart'))

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
    global _INITIATED, _LAST_CHECK, HEART

    # Make sure heart exists
    if not _INITIATED:
        HEART.touch()
        _INITIATED = True

    # Only check once a second
    if _LAST_CHECK and time.time() - _LAST_CHECK < 1.0:
        return

    if not HEART.exists():
        HEART.touch()
        raise RuntimeError("Missing heart")

    _LAST_CHECK = time.time()
