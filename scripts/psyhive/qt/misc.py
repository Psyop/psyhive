"""Miscellaneous tools for managing qt."""

import six

from psyhive.utils import get_result_storer
from psyhive.qt.wrapper.mgr import QtWidgets, QtCore, QtGui


@get_result_storer(ignore_args=True)
def get_application(name='any'):
    """Get QApplication object.

    Args:
        name (str): name for application

    Returns:
        (QApplication): qt application
    """
    _existing = QtWidgets.QApplication.instance()
    if _existing:
        return _existing
    return QtWidgets.QApplication([name])


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
    elif isinstance(icon, six.string_types):
        return QtGui.QIcon(icon)
    raise ValueError(icon)


def get_p(*args):
    """Get a point object from the given data.

    A QPoint, QSize, tuple, list or pair of values can be provided.

    Returns:
        (QPoint): point object
    """
    if len(args) == 1:
        _arg = args[0]
        if isinstance(_arg, (tuple, list)) and len(_arg) == 2:
            return QtCore.QPoint(*_arg)
        elif isinstance(_arg, (QtCore.QPoint, QtCore.QPointF)):
            return _arg
        elif isinstance(_arg, QtCore.QSize):
            return QtCore.QPoint(_arg.width(), _arg.height())
    elif len(args) == 2:
        return QtCore.QPoint(args[0], args[1])
    raise ValueError(args)


def get_size(*args):
    """Get a size from the given object.

    Returns:
        (QSize): size object
    """
    if len(args) == 1:
        _size = args[0]
        if isinstance(_size, QtCore.QSize):
            return _size
        elif isinstance(_size, QtCore.QPoint):
            return QtCore.QSize(_size.x(), _size.y())
        elif isinstance(_size, (tuple, list)):
            return QtCore.QSize(_size[0], _size[1])
        elif isinstance(_size, six.string_types):
            return QtCore.QSize(*[int(_token) for _token in _size.split('x')])
    elif len(args) == 2:
        return QtCore.QSize(*args)
    raise ValueError(args)


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
