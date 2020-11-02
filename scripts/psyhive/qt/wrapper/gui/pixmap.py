"""Override for QtGui.QPixmap."""

import os
import tempfile
import time

import six

from psyhive.utils import File, lprint, test_path, abs_path
from psyhive.qt.wrapper.mgr import QtGui, QtCore, Qt
from psyhive.qt.wrapper.gui.painter import HPainter

TEST_JPG = abs_path('{}/test.jpg'.format(tempfile.gettempdir()))
TEST_PNG = abs_path('{}/test.png'.format(tempfile.gettempdir()))
TEST_IMG = TEST_JPG


class HPixmap(QtGui.QPixmap):
    """Override for QPixmap object."""

    def add_circle(
            self, pos, col='black', radius=10, thickness=None,
            operation=None, pen=None):
        """Draw a circle on this pixmap.

        Args:
            pos (QPoint): centre point
            col (str): line colour
            radius (int): circle radius
            thickness (float): line thickness
            operation (str): compositing operation
            pen (QPen): override pen
        """
        from psyhive import qt

        _pos = qt.get_p(pos)
        _col = qt.get_col(col)
        _pen = pen or QtGui.QPen(_col)
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

        return _rect

    def add_dot(self, pos, col='black', radius=1.0, outline=None,
                thickness=None, operation=None, render_hint=None):
        """Draw a circle on this pixmap.

        Args:
            pos (QPoint): centre point
            col (str): dot colour
            radius (float): dot radius
            outline (QPen): apply outline pen
            thickness (float): line thickness
            operation (str): compositing operation
            render_hint (RenderHint): add render hint
        """
        from psyhive import qt

        _pos = qt.get_p(pos)
        _col = qt.get_col(col)
        _brush = QtGui.QBrush(_col)

        # Set outline
        if thickness:
            _pen = QtGui.QPen(qt.get_col('Black'))
            _pen.setWidthF(thickness)
        elif not outline:
            _pen = QtGui.QPen(_col)
            _pen.setStyle(Qt.NoPen)
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
        if render_hint:
            _pnt.setRenderHint(render_hint)
        _pnt.set_operation(operation)
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
            _pen.setCapStyle(Qt.RoundCap)
            _pen.setJoinStyle(Qt.RoundJoin)
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
        _rect = _get_rect(pos=_pos, size=_pix.size(), anchor=anchor)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.set_operation(operation)
        _pnt.drawPixmap(_rect.x(), _rect.y(), _pix)
        _pnt.end()

        return _rect

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
            _pen.setCapStyle(Qt.RoundCap)
            if thickness:
                _pen.setWidthF(thickness)

        _brush = QtGui.QBrush()
        _brush.setStyle(Qt.NoBrush)

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

        return _poly.boundingRect()

    def add_rect(self, pos, size, col='white', outline='black', operation=None,
                 anchor='TL', thickness=None):
        """Draw a rectangle on this pixmap.

        Args:
            pos (QPoint): position
            size (QSize): rectangle size
            col (str): rectangle colour
            outline (str): outline colour
            operation (str): overlay mode
            anchor (str): position anchor point
            thickness (float): line thickness
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
        if thickness:
            _pen.setWidthF(thickness)

        _pnt = HPainter()
        _pnt.begin(self)
        _pnt.set_operation(operation)
        _pnt.setPen(_pen)
        _pnt.setBrush(_brush)
        _pnt.drawRect(_rect)
        _pnt.end()

        return _rect

    def add_rounded_rect(self, pos, size, col='White', bevel=5, anchor='TL',
                         pen=None, outline=True, render_hint=None):
        """Draw a rounded rectangle on this pixmap.

        Args:
            pos (QPoint): position
            size (QSize): rectangle size
            col (str): rectangle fill colour
            bevel (int): edge bevel
            anchor (str): position anchor point
            pen (QPen): override pen
            outline (bool): show outline
            render_hint (str): force render hint

        Returns:
            (QRect): draw region
        """
        from psyhive import qt

        if isinstance(col, QtGui.QPixmap):
            _col = col
        else:
            _col = qt.get_col(col)
        _brush = QtGui.QBrush(_col)
        _rect = _get_rect(pos=pos, size=size, anchor=anchor)

        # Set pen
        _pen = None
        if pen:
            _pen = pen
        elif not outline:
            _pen = QtGui.QPen(_col)
            _pen.setStyle(Qt.NoPen)

        _pnt = qt.HPainter()
        _pnt.begin(self)
        _pnt.set_render_hint(render_hint)
        if _pen:
            _pnt.setPen(_pen)
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
            size=None, line_h=None):
        """Add text to pixmap.

        Args:
            text (str): text to add
            pos (tuple|QPoint): text position
            anchor (str): text anchor
            col (str|QColor): text colour
            font (QFont): text font
            size (int): font size
            line_h (int): override line height (draws each line separately)
        """
        _kwargs = locals()
        del _kwargs['self']

        if not isinstance(text, six.string_types):
            raise TypeError("Bad text type {} ({})".format(
                text, type(text).__name__))

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

    def copy(self, *args, **kwargs):
        """Make a duplicate of this pixmap.

        Returns:
            (HPixmap): duplicate
        """
        return HPixmap(super(HPixmap, self).copy(*args, **kwargs))

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

    def resize(self, width=None, height=None, use_img=True):
        """Return a resized version of this pixmap.

        Args:
            width (int): width in pixels
            height (int): height in pixels
            use_img (bool): use QImage.scaled (cleaner result)
        """
        if isinstance(width, (int, float)):
            _width = width
            _height = height or width
        elif isinstance(width, QtCore.QSize):
            _width = width.width()
            _height = width.height()
        elif width is None:
            assert height
            _height = height
            _width = _height*self.get_aspect()
        else:
            raise ValueError(width)

        if not use_img:  # Probably faster bad result
            _pix = QtGui.QPixmap.scaled(
                self, _width, _height,
                transformMode=Qt.SmoothTransformation)
        else:  # Smoother image
            _img = self.toImage()
            _img = _img.scaled(
                _width, _height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            _pix = QtGui.QPixmap.fromImage(_img)

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
                _result = qt.yes_no_cancel(
                    'Overwrite existing image?\n\n'+path)
                if _result == 'No':
                    return
            os.remove(_file.path)
        test_path(_file.dir)

        self.save(abs_path(path, win=os.name == 'nt'),
                  format=_fmt, quality=100)
        assert _file.exists()

    def save_test(self, file_=None, timestamp=True, extn='jpg', verbose=1):
        """Save test image and copy it to pictures dir.

        Args:
            file_ (str): override save file path - this can be used
                to switch this method with a regular save
            timestamp (bool): write timestamped file
            extn (str): test file extension
            verbose (int): print process data

        Returns:
            (str): path to saved file
        """
        if file_:
            self.save_as(file_, force=True)
            return file_

        _test_img = File(TEST_IMG).apply_extn(extn).path
        self.save_as(_test_img, verbose=verbose, force=True)
        _file = _test_img

        if timestamp:
            _timestamp_file = abs_path(time.strftime(
                '~/Documents/My Pictures/tests/%y%m%d_%H%M.{}'.format(extn)))
            self.save_as(_timestamp_file, verbose=verbose, force=True)
            _file = _timestamp_file

        return _file

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
        if self.hasAlpha():
            _tmp.setMask(self.mask())
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
    _pos = qt.get_p(pos)
    if anchor == 'C':
        _root = _pos - qt.get_p(_size)/2
    elif anchor == 'L':
        _root = _pos - qt.get_p(0, _size.height()/2)
    elif anchor == 'R':
        _root = _pos - qt.get_p(_size.width(), _size.height()/2)
    elif anchor == 'T':
        _root = _pos - qt.get_p(_size.width()/2, 0)
    elif anchor == 'TL':
        _root = _pos
    elif anchor == 'TR':
        _root = _pos - qt.get_p(_size.width(), 0)
    elif anchor == 'BL':
        _root = _pos - qt.get_p(0, _size.height())
    elif anchor == 'BR':
        _root = _pos - qt.get_p(_size.width(), _size.height())
    else:
        raise ValueError(anchor)

    return QtCore.QRect(_root, _size)
