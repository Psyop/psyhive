"""General utilities for the pipe module."""

import tempfile

from psyhive.utils import abs_path

TMP = abs_path(tempfile.gettempdir().replace('/usr/tmp', '/var/tmp'))


def read_ver_n(ver):
    """Get version number from a version token.

    Args:
        ver (str): version token (eg. v001)

    Returns:
        (int): version number

    Raises:
        (ValueError): if ver was not a valid version token
    """
    if not (
            ver[0].startswith('v') and
            ver[1:].isdigit() and
            len(ver) == 4):
        raise ValueError(ver)

    _ver_n = int(ver[1:])
    return _ver_n
