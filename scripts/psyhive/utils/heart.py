"""Tools for managing the check heart loop breaker tool."""

import os

_INITIATED = False


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

    global _INITIATED

    _heart = abs_path('~/.heart')
    if not _INITIATED:
        touch(_heart)
        _INITIATED = True

    if not os.path.exists(_heart):
        raise RuntimeError("Missing heart")
