"""Miscellaneous tools for managing qt."""

import functools
import os
import math
import traceback

import six

from psyhive.utils import get_result_storer, File

from .wrapper.mgr import QtWidgets, QtCore, QtGui, QtUiTools


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
        elif isinstance(col[0], int):
            _col = HColor(*col)
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
    elif isinstance(icon, QtGui.QIcon):
        return icon
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
        elif isinstance(_arg, (QtCore.QSize, QtCore.QSizeF)):
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
            _result = _size
        elif isinstance(_size, QtCore.QPoint):
            _result = QtCore.QSize(_size.x(), _size.y())
        elif isinstance(_size, (tuple, list)):
            _result = QtCore.QSize(_size[0], _size[1])
        elif isinstance(_size, six.string_types):
            _result = QtCore.QSize(*[
                int(_token) for _token in _size.split('x')])
        elif isinstance(_size, int):
            _result = QtCore.QSize(_size, _size)
        elif isinstance(_size, float):
            _result = QtCore.QSizeF(_size, _size)
        else:
            raise ValueError(args)
    elif len(args) == 2:
        _result = QtCore.QSize(*args)
    else:
        raise ValueError(args)
    return _result


def get_pixmap(pix):
    """Get pixmap from the given data.

    Args:
        pix (QPixmap|str): pixmap data or path to pixmap

    Returns:
        (HPixmap): pixmap object
    """
    from psyhive import qt, icons

    if isinstance(pix, qt.HPixmap):
        return pix
    elif isinstance(pix, QtGui.QPixmap):
        return qt.HPixmap(pix)
    elif isinstance(pix, six.string_types):
        if os.path.exists(pix):
            return qt.HPixmap(pix)
        return qt.HPixmap(icons.EMOJI.find(pix))
    elif isinstance(pix, File):
        return qt.HPixmap(pix.path)
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


def get_ui_loader():
    """Build ui loader object with psyhive overrides registered.

    Returns:
        (QUiLoader): ui loader
    """
    from psyhive import qt

    _loader = QtUiTools.QUiLoader()
    _loader.registerCustomWidget(qt.HCheckBox)
    _loader.registerCustomWidget(qt.HComboBox)
    _loader.registerCustomWidget(qt.HLabel)
    _loader.registerCustomWidget(qt.HListWidget)
    _loader.registerCustomWidget(qt.HPushButton)
    _loader.registerCustomWidget(qt.HTabWidget)
    _loader.registerCustomWidget(qt.HTextBrowser)
    _loader.registerCustomWidget(qt.HTreeWidget)

    return _loader


def get_vect(ang, dist):
    """Get point vector based on the given angle and distance.

    Args:
        ang (float): angle (in degrees)
        dist (float): vector length

    Returns:
        (QPoint): vector
    """
    _ang_r = math.radians(ang)
    return get_p(dist*math.cos(_ang_r), dist*math.sin(_ang_r))


def safe_timer_event(timer_event):
    """Decorator to execute timer event but kill timer if it errors.

    Args:
        timer_event (fn): timerEvent method

    Returns:
        (fn): safe method
    """

    @functools.wraps(timer_event)
    def _safe_exec_timer(dialog, event=None, **kwargs):

        # Try and exec timer event
        _destroy = False
        try:
            _result = timer_event(dialog, event=event, **kwargs)
        except Exception as _exc:
            _tb = traceback.format_exc().strip()
            print 'TIMER EVENT FAILED\n# '+'\n# '.join(_tb.split('\n'))
            _destroy = True
            _result = 1

        # Destroy if event has failed or interface no longer visbible
        if _destroy or not dialog.isVisible():
            dialog.killTimer(dialog.timer)
            dialog.closeEvent(None)
            dialog.deleteLater()

        return _result

    _safe_exec_timer.SAFE_TIMER = True

    return _safe_exec_timer
