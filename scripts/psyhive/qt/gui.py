"""Overrides for QtGui module."""

import os

from psyhive.utils import File, lprint, test_path, abs_path
from psyhive.qt.misc import get_p, get_pixmap, get_col
from psyhive.qt.mgr import QtGui, QtCore


class HColor(QtGui.QColor):
    """Override for QColor."""

    def to_tuple(self, mode='int'):
        """Get this colour's RGB data as a tuple.

        Args:
            mode (str): colour mode (int or float)

        Returns:
            (tuple): RGB values
        """
        if mode == 'int':
            return self.red(), self.green(), self.blue()
        elif mode == 'float':
            return self.red()/255.0, self.green()/255.0, self.blue()/255.0
        raise ValueError(mode)

    def __mul__(self, value):
        return HColor(
            self.red()*value, self.green()*value, self.blue()*value)

    def __str__(self):
        return '<{}:({})>'.format(
            type(self).__name__,
            ', '.join(['{:d}'.format(_val) for _val in self.to_tuple()]))


class HPainter(QtGui.QPainter):
    """Wrapper for QPainter object."""

    def add_text(
            self, text, pos=(0, 0), anchor='TL', col='white', font=None,
            verbose=0):
        """Write text to the image.

        Args:
            text (str): text to add
            pos (tuple|QPoint): text position
            anchor (str): text anchor
            col (str|QColor): text colour
            font (QFont): text font
            verbose (int): print process data
        """
        lprint("Adding text", text, verbose=verbose)
        _window = self.window()
        _pos = get_p(pos)
        _x, _y = _pos.x(), _pos.y()
        _w, _h = _window.width(), _window.height()

        if anchor == 'BL':
            _rect = QtCore.QRect(_x, 0, _w-_x, _y)
            _align = QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom
        elif anchor == 'BR':
            _rect = QtCore.QRect(0, 0, _x, _y)
            _align = QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom
        elif anchor == 'C':
            _rect = QtCore.QRect(0, 0, 2*_x, 2*_y)
            _align = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
        elif anchor == 'L':
            _rect = QtCore.QRect(_x, 0, _w, 2*_y)
            _align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
        elif anchor == 'R':
            _rect = QtCore.QRect(0, 0, _x, 2*_y)
            _align = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        elif anchor in ('T', 'TC'):
            _rect = QtCore.QRect(0, _y, _w, _h)
            _align = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop
        elif anchor == 'TL':
            _rect = QtCore.QRect(_x, _y, _w, _h)
            _align = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop
        elif anchor == 'TR':
            _rect = QtCore.QRect(0, _y, _x, _h-_y)
            _align = QtCore.Qt.AlignRight | QtCore.Qt.AlignTop
        else:
            raise ValueError('Unhandled anchor: %s' % anchor)

        if font:
            self.setFont(font)

        # Draw text
        self.setPen(get_col(col or 'white'))
        self.drawText(_rect, _align, text)


class HPixmap(QtGui.QPixmap):
    """Override for QPixmap object."""

    def add_text(
            self, text, pos=(0, 0), anchor='TL', col='black', font=None):
        """Add text to pixmap.

        Args:
            text (str): text to add
            pos (tuple|QPoint): text position
            anchor (str): text anchor
            col (str|QColor): text colour
            font (QFont): text font
        """
        _kwargs = locals()
        del _kwargs['self']

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.add_text(**_kwargs)
        _pnt.end()

    def add_overlay(self, pix, pos, anchor='TL', operation=None):
        """Add overlay to this pixmap.

        Args:
            pix (QPixmap|str): image to overlay
            pos (QPoint|tuple): position of overlay
            anchor (str): anchor position
            operation (str): overlay mode
        """
        _pix = get_pixmap(pix)
        _pos = get_p(pos)
        _pnt = QtGui.QPainter()

        # Set offset
        if anchor == 'C':
            _pos = _pos - get_p([_pix.width()/2, _pix.height()/2])
        elif anchor == 'BL':
            _pos = _pos - get_p([0, _pix.height()])
        elif anchor == 'BR':
            _pos = _pos - get_p([_pix.width(), _pix.height()])
        elif anchor == 'TL':
            pass
        elif anchor == 'TR':
            _pos = _pos - get_p([_pix.width(), 0])
        else:
            raise ValueError(anchor)

        _pnt.begin(self)

        # Set operation mode
        if operation is not None:
            _comp_mode = QtGui.QPainter.CompositionMode
            if operation == 'over':
                _mode = _comp_mode.CompositionMode_SourceOver
            elif operation == 'add':
                _mode = _comp_mode.CompositionMode_Plus
            elif operation == 'mult':
                _mode = _comp_mode.CompositionMode_Multiply
            else:
                raise ValueError(operation)
            _pnt.setCompositionMode(_mode)

        # Apply image
        _pnt.drawPixmap(_pos.x(), _pos.y(), _pix)

        _pnt.end()

    def resize(self, width, height):
        """Return a resized version of this pixmap.

        Args:
            width (int): width in pixels
            height (int): height in pixels
        """
        _pix = QtGui.QPixmap.scaled(
            self, width, height, transformMode=QtCore.Qt.SmoothTransformation)
        return HPixmap(_pix)

    def save_as(self, path, force=False, verbose=0):
        """Save this pixmap at the given path.

        Args:
            path (str): path to save at
            force (bool): force overwrite with no confirmation
            verbose (int): print process data
        """
        from psyhive import qt

        assert self.width() and self.height()

        _file = File(path)
        _fmt = {}.get(_file.extn, _file.extn.upper())
        lprint("SAVING", path, _fmt, verbose=verbose)
        if _file.exists():
            if not force:
                qt.ok_cancel('Overwrite existing image?\n\n'+path)
            os.remove(_file.path)
        test_path(_file.dir)

        self.save(abs_path(path, win=True), format=_fmt, quality=100)
        assert _file.exists()
