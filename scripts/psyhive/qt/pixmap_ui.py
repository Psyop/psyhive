"""Tools for managing interfaces controlled by a single updating pixmap."""

import sys

from psyhive.qt.wrapper import QtWidgets, HPixmap
from psyhive.qt.interface import safe_timer_event
from psyhive.qt.misc import get_size


class PixmapUi(QtWidgets.QDialog):
    """Base class for an interface with just an updating pixmap."""

    def __init__(self, size=(640, 640), base_col='red', fps=None, title=None,
                 mouse_tracking=False):
        """Constructor.

        Args:
            size (QSize): interface size
            base_col (str): base colour for pixmap
            fps (float): frame rate (if declared timer is started)
            title (str): interface title
            mouse_tracking (bool): add mouse tracking (mouseMoveEvent)
        """

        # Remove any existing intefaces
        _dialog_stack_key = type(self).__name__
        if _dialog_stack_key in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[_dialog_stack_key].deleteLater()
        sys.QT_DIALOG_STACK[_dialog_stack_key] = self

        super(PixmapUi, self).__init__()
        self.base_col = base_col

        # Set up interface/label
        self.setWindowTitle(title or type(self).__name__.strip('_'))
        _size = get_size(size)
        self.resize(_size)
        self._label = QtWidgets.QLabel(self)
        self._label.resize(_size)

        # Set up mouse tracking
        if mouse_tracking:
            self._label.setMouseTracking(True)
            self._label.mouseMoveEvent = self.mouseMoveEvent

        # Timer attrs
        self.pause = False
        self.timer = None
        if fps:
            self.timer = self.startTimer(1000.0/fps)

        self.redraw()
        self.show()

    def delete(self):
        """Delete this interface."""
        self.deleteLater()

    def redraw(self):
        """Redraw interface."""
        _size = self.size()
        _pix = HPixmap(_size)
        _pix.fill(self.base_col)
        self.update_pixmap(_pix)
        self._label.setPixmap(_pix)

    def update_pixmap(self, pix):
        """Update interface pixmap.

        Args:
            pix (QPixmap): pixmap to update
        """

    def resizeEvent(self, event):
        """Executed on resize.

        Args:
            event (QEvent): resize event
        """
        super(PixmapUi, self).resizeEvent(event)
        self._label.resize(self.size())
        self.redraw()

    @safe_timer_event
    def timerEvent(self, event):
        """Executed on timer tick.

        Args:
            event (QEvent): timer event
        """
        super(PixmapUi, self).timerEvent(event)
        self.redraw()
