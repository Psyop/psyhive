"""Override for QtGui.Painter."""

from psyhive.utils import lprint
from psyhive.qt.wrapper.mgr import QtGui, QtCore, Qt


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
            _align = Qt.AlignLeft | Qt.AlignBottom
        elif anchor == 'BR':
            _rect = QtCore.QRect(0, 0, _x, _y)
            _align = Qt.AlignRight | Qt.AlignBottom
        elif anchor == 'B':
            _rect = QtCore.QRect(0, 0, 2*_x, _y)
            _align = Qt.AlignHCenter | Qt.AlignBottom
        elif anchor == 'C':
            _rect = QtCore.QRect(0, 0, 2*_x, 2*_y)
            _align = Qt.AlignHCenter | Qt.AlignVCenter
        elif anchor == 'L':
            _rect = QtCore.QRect(_x, 0, _w, 2*_y)
            _align = Qt.AlignVCenter | Qt.AlignLeft
        elif anchor == 'R':
            _rect = QtCore.QRect(0, 0, _x, 2*_y)
            _align = Qt.AlignRight | Qt.AlignVCenter
        elif anchor in ('T', 'TC'):
            _rect = QtCore.QRect(0, _y, 2*_x, _h)
            _align = Qt.AlignHCenter | Qt.AlignTop
        elif anchor == 'TL':
            _rect = QtCore.QRect(_x, _y, _w, _h)
            _align = Qt.AlignLeft | Qt.AlignTop
        elif anchor == 'TR':
            _rect = QtCore.QRect(0, _y, _x, _h-_y)
            _align = Qt.AlignRight | Qt.AlignTop
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
