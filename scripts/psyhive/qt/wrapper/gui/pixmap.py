"""Override for QtGui.QPixmap."""

import os
import tempfile
import time

import six

from psyhive.utils import File, lprint, test_path, abs_path
from psyhive.qt.wrapper.mgr import QtGui, QtCore, Qt
from psyhive.qt.wrapper.gui.painter import HPainter


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
        _pnt.setBrush(_brush)
        _pnt.setPen(_pen)
        _pnt.drawEllipse(
            _pos.x()-radius, _pos.y()-radius, radius*2, radius*2)
        _pnt.end()

    def add_line(
            self, pt1, pt2, col='black', thickness=None, operation=None,
            pen=None, verbose=0):
        """Draw a straight line on this pixmap.

        Args:
            pt1 (QPoint): start point
            pt2 (QPoint): end point
            col (str): line colour
            thickness (float): line thickness
            operation (str): compositing operation
            pen (QPen): override pen (ignores all other pen attrs)
            verbose (int): print process data
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

            lprint("COL", _col, verbose=verbose)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.setPen(_pen)
        _pnt.set_operation(operation)
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

        Returns:
            (QRect): rectangle that was drawn
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

        return QtCore.QRect(_pos, _pix.size())

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
        _pnt.setPen(_pen)
        _pnt.setBrush(_brush)
        _pnt.drawPath(_path)
        _pnt.end()

    def add_polygon(self, pts, col, outline='black', thickness=1.0):
        """Draw a polygon on this pixmap.

        Args:
            pts (QPointF list): polygon points
            col (QColor): fill colour
            outline (str|None): outline colour (if any)
            thickness (float): line thickness
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
        _pnt.setBrush(_brush)
        _pnt.setPen(_pen)
        _pnt.drawPolygon(_poly)
        _pnt.end()

    def add_rect(self, pos, size, col='white', outline='black', operation=None,
                 anchor='TL'):
        """Draw a rectangle on this pixmap.

        Args:
            pos (QPoint): position
            size (QSize): rectangle size
            col (str): rectangle colour
            outline (str): outline colour
            operation (str): overlay mode
            anchor (str): position anchor point
        """
        from psyhive import qt

        _col = qt.get_col(col)
        _brush = QtGui.QBrush(_col)
        _rect = _get_rect(pos=pos, size=size, anchor=anchor)

        # Set outline
        if outline:
            _pen = QtGui.QPen(outline)
        else:
            _pen = QtGui.QPen()
            _pen.setStyle(Qt.NoPen)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.set_operation(operation)
        _pnt.setPen(_pen)
        _pnt.setBrush(_brush)
        _pnt.drawRect(_rect)
        _pnt.end()

        return _rect

    def add_rounded_rect(self, pos, size, col, bevel=5, anchor='TL'):
        """Draw a rounded rectangle on this pixmap.

        Args:
            pos (QPoint): position
            size (QSize): rectangle size
            col (str): rectangle fill colour
            bevel (int): edge bevel
            anchor (str): position anchor point

        Returns:
            (QPixmap): updated pixmap
        """
        from psyhive import qt

        _col = qt.get_col(col)
        _brush = QtGui.QBrush(qt.get_col(_col))
        _rect = _get_rect(pos=pos, size=size, anchor=anchor)

        _pnt = qt.HPainter()
        _pnt.begin(self)
        _pnt.setBrush(_brush)
        _pnt.drawRoundedRect(_rect, bevel, bevel)
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
        from psyhive import qt

        _pos = qt.get_p(pos)
        _size = qt.get_size(size)
        _rect = QtCore.QRect(_pos, _size)

        _brush = QtGui.QBrush(qt.HColor(0, 0, 0, 0))
        _col = qt.get_col(col)
        _pen = QtGui.QPen(_col)
        if thickness:
            _pen.setWidthF(thickness)

        _pnt = qt.HPainter()
        _pnt.begin(self)
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

        if not isinstance(text, six.string_types):
            raise TypeError("Bad text type {} ({})".format(
                text, type(text).__name___))

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.add_text(**_kwargs)
        _pnt.end()

    def center(self):
        """Get centrepoint of this pixmap.

        Returns:
            (QPoint): centre
        """
        return self.rect().center()

    def contains(self, pos):
        """Check if the point falls inside this pixmap.

        Args:
            pos (QPoint): point to check

        Returns:
            (bool): whether point falls inside
        """
        return self.rect().contains(pos)

    def darken(self, factor):
        """Darken this pixmap (1 makes the pixmap black).

        Args:
            factor (float): how much to darken

        Returns:
            (HPixmap): this pixmap
        """
        from psyhive import qt
        _tmp = HPixmap(self.size())
        _tmp.fill(qt.HColor(0, 0, 0, 255*factor))
        self.add_overlay(_tmp, operation='over')
        return self

    def get_aspect(self):
        """Get aspect ratio of this image.

        Returns:
            (float): aspect ratio
        """
        return 1.0*self.width()/self.height()

    def get_c(self):
        """Get centre point of this pixmap.

        Returns:
            (QPoint): centre
        """
        from psyhive import qt
        return qt.get_p(self.size())/2

    def rotated(self, degrees):
        """Get a rotated version of this pixmap.

        Args:
            degrees (float): rotation to apply

        Returns:
            (QPixmap): rotate pixmap
        """
        _tfm = QtGui.QTransform()
        _tfm.rotate(degrees)
        return HPixmap(self.transformed(_tfm))

    def resize(self, width, height=None):
        """Return a resized version of this pixmap.

        Args:
            width (int): width in pixels
            height (int): height in pixels
        """
        if isinstance(width, (int, float)):
            _width = width
            _height = height or width
        elif isinstance(width, QtCore.QSize):
            _width = width.width()
            _height = width.height()
        else:
            raise ValueError(width)
        _pix = QtGui.QPixmap.scaled(
            self, _width, _height,
            transformMode=Qt.SmoothTransformation)
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

    def whiten(self, factor):
        """Whiten this pixmap (1 makes the pixmap white).

        Args:
            factor (float): how much to whiten

        Returns:
            (HPixmap): this pixmap
        """
        from psyhive import qt
        _tmp = HPixmap(self.size())
        _fill = qt.HColor(255, 255, 255, 255*factor)
        _tmp.fill(_fill)
        self.add_overlay(_tmp, operation='over')
        return self


def _get_rect(anchor, pos, size):
    """Get rect for the given pos/size and anchor position.

    Args:
        anchor (str): anchor point
        pos (QPoint): anchor position
        size (QSize): rect size

    Returns:
        (QRect): rectangle
    """
    from psyhive import qt

    _size = qt.get_size(size)
    if anchor == 'C':
        _pos = pos - qt.get_p(_size)/2
    elif anchor == 'L':
        _pos = pos - qt.get_p(0, _size.height()/2)
    elif anchor == 'TL':
        _pos = qt.get_p(pos)
    else:
        raise ValueError(anchor)

    return QtCore.QRect(_pos, _size)
