"""Overrides for QtGui module."""

import os

from psyhive.utils import File, lprint, test_path
from psyhive.qt.misc import get_p, get_pixmap
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


class HPixmap(QtGui.QPixmap):
    """Override for QPixmap object."""

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
        _pnt.begin(self)
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

        lprint("SAVING", path, verbose=verbose)
        _path = File(path)
        _fmt = {}.get(_path.extn, _path.extn.upper())
        if not force and _path.exists():
            qt.ok_cancel('Overwrite existing image?\n\n'+path)
        test_path(_path.dir)
        self.save(path, format=_fmt)
        assert os.path.exists(path)
