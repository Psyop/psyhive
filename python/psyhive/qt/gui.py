"""Overrides for QtGui module."""

import os

from psyhive.utils import File, abs_path, lprint
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

    def resize(self, width, height):
        """Return a resized version of this pixmap.

        Args:
            width (int): width in pixels
            height (int): height in pixels
        """
        _pix = QtGui.QPixmap.scaled(
            self, width, height, transformMode=QtCore.Qt.SmoothTransformation)
        return HPixmap(_pix)

    def save_as(self, path, verbose=0):
        """Save this pixmap at the given path.

        Args:
            path (str): path to save at
            verbose (int): print process data
        """
        lprint("SAVING", path, verbose=verbose)
        _path = File(path)
        _fmt = {}.get(_path.extn, _path.extn.upper())
        _save_path = abs_path(path, win=True)
        print _save_path
        self.save(_save_path, format=_fmt)
        assert os.path.exists(path)
