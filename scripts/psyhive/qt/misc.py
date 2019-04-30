"""Miscellaneous tools for managing qt."""

import sys

import six

from psyhive.utils import store_result
from psyhive.qt.mgr import QtWidgets, QtCore, QtGui


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


def get_p(pos):
    """Get a point object from the given data.

    Args:
        pos (tuple|list|QPoint): point data

    Returns:
        (QPoint): point object
    """
    if isinstance(pos, (tuple, list)) and len(pos) == 2:
        return QtCore.QPoint(*pos)
    elif isinstance(pos, QtCore.QPoint):
        return pos
    elif isinstance(pos, QtCore.QSize):
        return QtCore.QPoint(pos.width(), pos.height())
    raise ValueError(pos)


def get_pixmap(pix):
    """Get pixmap from the given data.

    Args:
        pix (QPixmap|str): pixmap data or path to pixmap

    Returns:
        (HPixmap): pixmap object
    """
    from psyhive import qt

    if isinstance(pix, qt.HPixmap):
        return pix
    elif isinstance(pix, QtGui.QPixmap):
        return qt.HPixmap(pix)
    elif isinstance(pix, six.string_types):
        return qt.HPixmap(pix)
    raise ValueError(pix)


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
