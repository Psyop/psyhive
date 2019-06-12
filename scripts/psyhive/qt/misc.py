"""Miscellaneous tools for managing qt."""

import sys

import six

from psyhive.utils import store_result
from psyhive.qt.wrapper.mgr import QtWidgets, QtCore, QtGui


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
    from psyhive.qt.wrapper import HColor
    if isinstance(col, six.string_types):
        _col = HColor(col)
    elif isinstance(col, HColor):
        _col = col
    elif isinstance(col, QtGui.QColor):
        _col = HColor(col)
    elif isinstance(col, (list, tuple)):
        assert len(col) == 3
        if isinstance(col[0], float):
            _col = HColor(QtGui.QColor.fromRgbF(*col))
        else:
            raise ValueError(col)
    else:
        raise ValueError(col)
    return _col


def get_icon(icon):
    """Build an icon based on the given input.

    Args:
        icon (QPixmap): input icon

    Returns:
        (QIcon): icon
    """
    if isinstance(icon, QtGui.QPixmap):
        return QtGui.QIcon(icon)
    raise ValueError(icon)


def get_p(pos):
    """Get a point object from the given data.

    Args:
        pos (tuple|list|QPoint): point data

    Returns:
        (QPoint): point object
    """
    if isinstance(pos, (tuple, list)) and len(pos) == 2:
        return QtCore.QPoint(*pos)
    elif isinstance(pos, (QtCore.QPoint, QtCore.QPointF)):
        return pos
    elif isinstance(pos, QtCore.QSize):
        return QtCore.QPoint(pos.width(), pos.height())
    raise ValueError(pos)


def get_size(size):
    """Get a size from the given object.

    Args:
        size (QSize|QPoint): object to convert

    Returns:
        (QSize): size object
    """
    if isinstance(size, QtCore.QSize):
        return size
    elif isinstance(size, QtCore.QPoint):
        return QtCore.QSize(size.x(), size.y())
    elif isinstance(size, (tuple, list)):
        return QtCore.QSize(size[0], size[1])
    raise ValueError(size)


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
