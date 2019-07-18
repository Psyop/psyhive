"""Overrides for QtGui module."""

import os
import tempfile
import time

import six

from psyhive.utils import File, lprint, test_path, abs_path
from psyhive.qt.wrapper.mgr import QtGui, QtCore, Qt


class HColor(QtGui.QColor):
    """Override for QColor."""

    def blacken(self, val):
        """Whiten this colour by the given fraction (1 returns white).

        Args:
            val (float): whiten fraction

        Returns:
            (HColor): whitened colour
        """
        return self*(1-val) + HColor('black')*val

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

    def whiten(self, val):
        """Whiten this colour by the given fraction (1 returns white).

        Args:
            val (float): whiten fraction

        Returns:
            (HColor): whitened colour
        """
        return self*(1-val) + HColor('white')*val

    def __add__(self, other):
        return HColor(
            self.red() + other.red(),
            self.green() + other.green(),
            self.blue() + other.blue())

    def __mul__(self, value):
        return HColor(
            self.red() * value,
            self.green() * value,
            self.blue() * value)

    def __str__(self):
        return '<{}:({})>'.format(
            type(self).__name__,
            ', '.join(['{:d}'.format(_val) for _val in self.to_tuple()]))

    def __sub__(self, other):
        return HColor(
            self.red() - other.red(),
            self.green() - other.green(),
            self.blue() - other.blue())


class HPainter(QtGui.QPainter):
    """Wrapper for QPainter object."""

    def add_text(
            self, text, pos=(0, 0), anchor='TL', col='white', font=None,
            size=None, verbose=0):
        """Write text to the image.

        Args:
            text (str): text to add
            pos (tuple|QPoint): text position
            anchor (str): text anchor
            col (str|QColor): text colour
            font (QFont): text font
            size (int): apply font size
            verbose (int): print process data
        """
        from psyhive.qt import get_p, get_col
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
        elif size is not None:
            _font = QtGui.QFont()
            _font.setPointSize(size)
            self.setFont(_font)

        # Draw text
        self.setPen(get_col(col or 'white'))
        self.drawText(_rect, _align, text)

    def set_operation(self, operation):
        """Set compositing operation.

        Args:
            operation (str): operation to apply
        """
        if operation is None:
            return
        elif operation in ['add', 'plus']:
            _mode = self.CompositionMode.CompositionMode_Plus
        elif operation == 'darken':
            _mode = self.CompositionMode.CompositionMode_Darken
        elif operation == 'lighten':
            _mode = self.CompositionMode.CompositionMode_Lighten
        elif operation in ['multiply', 'mult']:
            _mode = self.CompositionMode.CompositionMode_Multiply
        elif operation == 'over':
            _mode = self.CompositionMode.CompositionMode_SourceOver
        elif operation == 'soft':
            _mode = self.CompositionMode.CompositionMode_SoftLight
        elif operation == 'source':
            _mode = self.CompositionMode.CompositionMode_Source
        else:
            raise ValueError(operation)
        self.setCompositionMode(_mode)


class HPixmap(QtGui.QPixmap):
    """Override for QPixmap object."""

    def add_circle(
            self, pos, col='black', radius=10, thickness=None,
            operation=None):
        """Draw a circle on this pixmap.

        Args:
            pos (QPoint): centre point
            col (str): line colour
            radius (int): circle radius
            thickness (float): line thickness
            operation (str): compositing operation
        """
        from psyhive import qt

        _pos = qt.get_p(pos)
        _col = qt.get_col(col)
        _pen = QtGui.QPen(_col)
        if thickness:
            _pen.setWidthF(thickness)
        _rect = QtCore.QRect(
            _pos.x()-radius, _pos.y()-radius, radius*2, radius*2)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.set_operation(operation)
        _pnt.setRenderHint(HPainter.Antialiasing, 1)
        _pnt.setPen(_pen)
        _pnt.drawArc(_rect, 0, 360*16)
        _pnt.end()

    def add_dot(self, pos, col='black', radius=1.0, outline=None):
        """Draw a circle on this pixmap.

        Args:
            pos (QPoint): centre point
            col (str): dot colour
            radius (float): dot radius
            outline (QPen): apply outline pen
        """
        from psyhive import qt

        _pos = qt.get_p(pos)
        _col = qt.get_col(col)
        _brush = QtGui.QBrush(_col)

        # Set outline
        if not outline:
            _pen = QtGui.QPen(_col)
            _pen.setStyle(QtCore.Qt.NoPen)
        elif isinstance(outline, QtGui.QPen):
            _pen = outline
        elif isinstance(outline, six.string_types):
            _out_col = qt.get_col(outline)
            _pen = QtGui.QPen(_out_col)
        else:
            raise ValueError(outline)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.setRenderHint(HPainter.Antialiasing, 1)
        _pnt.setBrush(_brush)
        _pnt.setPen(_pen)
        _pnt.drawEllipse(
            _pos.x()-radius, _pos.y()-radius, radius*2, radius*2)
        _pnt.end()

    def add_line(
            self, pt1, pt2, col='black', thickness=None, operation=None,
            pen=None):
        """Draw a straight line on this pixmap.

        Args:
            pt1 (QPoint): start point
            pt2 (QPoint): end point
            col (str): line colour
            thickness (float): line thickness
            operation (str): compositing operation
            pen (QPen): override pen (ignores all other pen attrs)
        """
        from psyhive import qt

        _pt1 = qt.get_p(pt1)
        _pt2 = qt.get_p(pt2)

        # Get pen
        if pen:
            _pen = pen
        else:
            _col = qt.get_col(col)
            _pen = QtGui.QPen(_col)
            _pen.setCapStyle(QtCore.Qt.RoundCap)
            _pen.setJoinStyle(QtCore.Qt.RoundJoin)
            if thickness:
                _pen.setWidthF(thickness)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.set_operation(operation)
        _pnt.setRenderHint(HPainter.HighQualityAntialiasing, 1)
        _pnt.setPen(_pen)
        _pnt.drawLine(_pt1.x(), _pt1.y(), _pt2.x(), _pt2.y())
        _pnt.end()

    def add_overlay(
            self, pix, pos=None, anchor='TL', operation=None, resize=None):
        """Add overlay to this pixmap.

        Args:
            pix (QPixmap|str): image to overlay
            pos (QPoint|tuple): position of overlay
            anchor (str): anchor position
            operation (str): overlay mode
            resize (int|QSize): apply resize to overlay
        """
        from psyhive import qt
        _pix = qt.get_pixmap(pix)
        if resize:
            _pix = _pix.resize(resize)
        _pos = qt.get_p(pos) if pos else QtCore.QPoint()

        # Set offset
        if anchor == 'C':
            _pos = _pos - qt.get_p([_pix.width()/2, _pix.height()/2])
        elif anchor == 'BL':
            _pos = _pos - qt.get_p([0, _pix.height()])
        elif anchor == 'BR':
            _pos = _pos - qt.get_p([_pix.width(), _pix.height()])
        elif anchor == 'TL':
            pass
        elif anchor == 'TR':
            _pos = _pos - qt.get_p([_pix.width(), 0])
        else:
            raise ValueError(anchor)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.set_operation(operation)
        _pnt.drawPixmap(_pos.x(), _pos.y(), _pix)
        _pnt.end()

    def add_path(self, pts, col='black', thickness=None, pen=None):
        """Draw a path on this pixmap.

        Args:
            pts (QPoint list): list of points in path
            col (str): path colour
            thickness (float): line thickness
            pen (QPen): override pen (ignores all other pen attrs)
        """
        from psyhive import qt

        # Set pen
        if pen:
            _pen = pen
        else:
            _col = qt.get_col(col)
            _pen = pen or QtGui.QPen(_col)
            _pen.setCapStyle(QtCore.Qt.RoundCap)
            if thickness:
                _pen.setWidthF(thickness)

        _brush = QtGui.QBrush()
        _brush.setStyle(QtCore.Qt.NoBrush)

        # Make path object
        _path = QtGui.QPainterPath()
        _path.moveTo(qt.get_p(pts[0]))
        for _pt in pts[1:]:
            _path.lineTo(qt.get_p(_pt))

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.setRenderHint(HPainter.HighQualityAntialiasing, 1)
        _pnt.setPen(_pen)
        _pnt.setBrush(_brush)
        _pnt.drawPath(_path)
        _pnt.end()

    def add_polygon(self, pts, col, outline='black', thickness=1.0, verbose=0):
        """Draw a polygon on this pixmap.

        Args:
            pts (QPointF list): polygon points
            col (QColor): fill colour
            outline (str|None): outline colour (if any)
            thickness (float): line thickness
            verbose (int): print process data
        """
        from psyhive import qt

        if outline:
            _pen = QtGui.QPen(outline)
            _pen.setCapStyle(Qt.RoundCap)
            if thickness:
                _pen.setWidthF(thickness)
        else:
            _pen = QtGui.QPen()
            _pen.setStyle(Qt.NoPen)

        _col = qt.get_col(col)
        _brush = QtGui.QBrush(_col)
        _poly = QtGui.QPolygonF()
        for _pt in pts:
            _pt = qt.get_p(_pt)
            _poly.append(_pt)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.setRenderHint(HPainter.HighQualityAntialiasing, 1)
        _pnt.setBrush(_brush)
        _pnt.setPen(_pen)
        _pnt.drawPolygon(_poly)
        _pnt.end()

    def add_rect(self, pos, size, col, outline='black', operation=None):
        """Draw a rectangle on this pixmap.

        Args:
            pos (QPoint): position
            size (QSize): rectangle size
            col (str): rectangle colour
            outline (str): outline colour
            operation (str): overlay mode
        """
        from psyhive.qt import get_p, get_size, get_col

        _col = get_col(col)
        _brush = QtGui.QBrush(_col)
        _pos = get_p(pos)
        _size = get_size(size)
        if outline:
            _pen = QtGui.QPen(outline)
        else:
            _pen = QtGui.QPen()
            _pen.setStyle(Qt.NoPen)

        _rect = QtCore.QRect(_pos, _size)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.set_operation(operation)
        _pnt.setRenderHint(HPainter.HighQualityAntialiasing, 1)
        _pnt.setPen(_pen)
        _pnt.setBrush(_brush)
        _pnt.drawRect(_rect)
        _pnt.end()

        return _rect

    def add_square(self, pos, size, col='black', thickness=None):
        """Draw a square.

        Args:
            pos (QPoint): square position
            size (QSize): square size
            col (str): square colour
            thickness (float): line thickness
        """
        from psyhive.qt import get_p, get_size, get_col

        _pos = get_p(pos)
        _size = get_size(size)
        _rect = QtCore.QRect(_pos, _size)

        _brush = QtGui.QBrush(HColor(0, 0, 0, 0))
        _col = get_col(col)
        _pen = QtGui.QPen(_col)
        if thickness:
            _pen.setWidthF(thickness)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.setRenderHint(HPainter.HighQualityAntialiasing, 1)
        _pnt.setPen(_pen)
        _pnt.setBrush(_brush)
        _pnt.drawRect(_rect)
        _pnt.end()

        return _rect

    def add_text(
            self, text, pos=(0, 0), anchor='TL', col='black', font=None,
            size=None):
        """Add text to pixmap.

        Args:
            text (str): text to add
            pos (tuple|QPoint): text position
            anchor (str): text anchor
            col (str|QColor): text colour
            font (QFont): text font
            size (int): font size
        """
        _kwargs = locals()
        del _kwargs['self']

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.setRenderHint(HPainter.HighQualityAntialiasing, 1)
        _pnt.add_text(**_kwargs)
        _pnt.end()

    def darken(self, factor):
        """Darken this pixmap (1 makes the pixmap black).

        Args:
            factor (float): how much to darken
        """
        _tmp = HPixmap(self.size())
        _tmp.fill(HColor(0, 0, 0, 255*factor))
        self.add_overlay(_tmp, operation='mult')

    def get_c(self):
        """Get centre point of this pixmap.

        Returns:
            (QPoint): centre
        """
        from psyhive import qt
        return qt.get_p(self.size())/2

    def resize(self, width, height=None):
        """Return a resized version of this pixmap.

        Args:
            width (int): width in pixels
            height (int): height in pixels
        """
        if isinstance(width, int):
            _width = width
            _height = height or width
        elif isinstance(width, QtCore.QSize):
            _width = width.width()
            _height = width.height()
        else:
            raise ValueError(width)
        _pix = QtGui.QPixmap.scaled(
            self, _width, _height,
            transformMode=QtCore.Qt.SmoothTransformation)
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

    def save_test(self, file_=None):
        """Save test image and copy it to pictures dir.

        Args:
            file_ (str): override save file path - this can be used
                to switch this method with a regular save

        Returns:
            (str): path to saved file
        """
        if file_:
            self.save_as(file_, force=True)
            return file_
        _tmp_file = abs_path('{}/test.jpg'.format(tempfile.gettempdir()))
        _pics_file = abs_path(time.strftime(
            '~/Documents/My Pictures/tests/%y%m%d_%H%M.jpg'))
        self.save_as(_tmp_file, verbose=1, force=True)
        self.save_as(_pics_file, verbose=1, force=True)
        return _pics_file
