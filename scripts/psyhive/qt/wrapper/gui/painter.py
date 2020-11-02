"""Override for QtGui.Painter."""

from psyhive.utils import lprint
from psyhive.qt.wrapper.mgr import QtGui, QtCore, Qt


class HPainter(QtGui.QPainter):
    """Wrapper for QPainter object."""

    def begin(self, *args, **kwargs):
        """Begin painting."""
        super(HPainter, self).begin(*args, **kwargs)
        self.setRenderHint(self.SmoothPixmapTransform, True)

    def add_text(
            self, text, pos=(0, 0), anchor='TL', col='white', font=None,
            size=None, line_h=None, verbose=0):
        """Write text to the image.

        Args:
            text (str): text to add
            pos (tuple|QPoint): text position
            anchor (str): text anchor
            col (str|QColor): text colour
            font (QFont): text font
            size (int): apply font size
            line_h (int): override line height (draws each line separately)
            verbose (int): print process data
        """
        _kwargs = locals()
        del _kwargs['self']
        from psyhive import qt

        # Add by line if line height declared
        if line_h is not None and '\n' in text:
            self._add_text_lines(**_kwargs)
            return

        lprint("Adding text", text, verbose=verbose)
        _window = self.window()
        _pos = qt.get_p(pos)
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

        # Setup font
        if font:
            self.setFont(font)
        elif size is not None:
            _font = QtGui.QFont()
            _font.setPointSize(size)
            self.setFont(_font)

        # Draw text
        self.setPen(qt.get_col(col or 'white'))
        self.drawText(_rect, _align, text)

    def _add_text_lines(
            self, text, line_h, pos=(0, 0), anchor='TL', col='white',
            font=None, size=None, verbose=0):
        """Add lines of text.

        Args:
            text (str): text to add
            line_h (int): override line height (draws each line separately)
            pos (tuple|QPoint): text position
            anchor (str): text anchor
            col (str|QColor): text colour
            font (QFont): text font
            size (int): apply font size
            verbose (int): print process data
        """
        _kwargs = locals()
        del _kwargs['self']
        del _kwargs['line_h']
        from psyhive import qt

        _lines = text.split('\n')
        if anchor.startswith('B'):
            _lines.reverse()
        for _idx, _line in enumerate(_lines):

            # Set offset
            _offs = _idx*line_h
            if anchor.startswith('B'):
                _offs *= -1
            elif anchor in 'LCR':
                _offs -= 0.5 * line_h * (len(_lines)-1)

            # Draw line
            _kwargs['pos'] = qt.get_p(pos) + qt.Y_AXIS*_offs
            _kwargs['text'] = _line
            self.add_text(**_kwargs)

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

    def set_render_hint(self, hint):
        """Set current render hint.

        Args:
            hint (str|RenderHint|None): hint to apply
        """
        if hint is None:
            return

        if isinstance(hint, self.RenderHint):
            _hint = hint
        elif hint == 'Antialiasing':
            _hint = self.Antialiasing
        elif hint == 'TextAntialiasing':
            _hint = self.TextAntialiasing
        elif hint == 'SmoothPixmapTransform':
            _hint = self.SmoothPixmapTransform
        elif hint == 'HighQualityAntialiasing':
            _hint = self.HighQualityAntialiasing
        elif hint == 'NonCosmeticDefaultPen':
            _int = self.NonCosmeticDefaultPen
        elif hint == 'LosslessImageRendering':
            _hint = self.LosslessImageRendering
        else:
            raise ValueError(hint)
        self.setRenderHint(_hint)
