"""Miscellaneous tools for managing qt."""

import sys

import six

from psyhive.utils import store_result
from psyhive.qt.mgr import QtWidgets


@store_result
def get_application():
    """Get QApplication object.

    Returns:
        (QApplication): qt application
    """
    if 'maya.cmds' in sys.modules:
        return QtWidgets.QApplication.instance()
    return QtWidgets.QApplication(['any'])


def get_col(col):
    """Get a QColor object based on the given input.

    Args:
        col (str): input colour

    Returns:
        (HColor): match qt colour object
    """
    from psyhive.qt.gui import HColor
    if isinstance(col, six.string_types):
        _col = HColor(col)
    else:
        raise ValueError(col)
    return _col


def get_qt_str(obj):
    """Get qt display string for the given object.

    Args:
        obj (object): object to test
    """
    if hasattr(obj, 'get_qt_str'):
        _result = obj.get_qt_str()
    else:
        _result = str(obj)
    return _result
