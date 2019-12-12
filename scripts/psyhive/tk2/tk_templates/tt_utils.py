"""Utilities for managing tank template representations."""

from psyhive.utils import abs_path

from psyhive.tk2.tk_utils import get_current_engine


def get_area(path):
    """Get work area - asset or shot.

    Args:
        path (str): path to test

    Returns:
        (str): work area
    """
    _path = abs_path(path)
    if '/sequences/' in _path or _path.endswith('/sequences'):
        return 'shot'
    elif '/assets/' in _path:
        return 'asset'

    raise ValueError(path)


def get_dcc(path, allow_none=False):
    """Read dcc from the given path.

    Args:
        path (str): path to test
        allow_none (bool): allow no dcc

    Returns:
        (str|None): dcc name (if any)
    """
    _path = abs_path(path)
    if '/maya/' in path or _path.endswith('/maya'):
        return 'maya'
    elif '/houdini/' in path or _path.endswith('/houdini'):
        return 'houdini'
    elif '/nuke/' in path or _path.endswith('/nuke'):
        return 'nuke'
    elif allow_none:
        return None

    raise ValueError(path)


def get_extn(dcc):
    """Get a suggested extension for the given dcc.

    Args:
        dcc (str): name of dcc

    Returns:
        (str): suggest file extn
    """
    return {
        'maya': 'ma',
        'nuke': 'nk',
        'houdini': 'hip',
    }[dcc]


def get_template(hint):
    """Get template matching the given hint.

    Args:
        hint (str): hint to match

    Returns:
        (TemplatePath): tank template
    """
    return get_current_engine().tank.templates[hint]
