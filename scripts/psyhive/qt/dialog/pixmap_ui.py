"""Tools for managing interfaces controlled by a single updating pixmap."""

import sys

from ..wrapper import QtWidgets, HPixmap
from ..misc import get_size, safe_timer_event


class HPixmapUi(QtWidgets.QDialog):
    """Base class for an interface with just an updating pixmap."""

    def __init__(self, size=(640, 640), base_col='red', fps=None, title=None,
                 mouse_tracking=False, parent=None, show=True):
        """Constructor.

        Args:
            size (QSize): interface size
            base_col (str): base colour for pixmap
            fps (float): frame rate (if declared timer is started)
            title (str): interface title
            mouse_tracking (bool): add mouse tracking (mouseMoveEvent)
            parent (QDialog): parent dialog
            show (bool): show interface on launch
        """
        from psyhive import host

        self.base_col = base_col

        # Remove any existing intefaces
        _dialog_stack_key = type(self).__name__
        if _dialog_stack_key in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[_dialog_stack_key].delete()
        sys.QT_DIALOG_STACK[_dialog_stack_key] = self

        # Init base class
        _kwargs = {}
        _parent = parent or host.get_main_window_ptr()
        if _parent:
            _kwargs['parent'] = _parent
        super(HPixmapUi, self).__init__(**_kwargs)

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
        if show:
            self.show()

    def delete(self):
        """Delete this interface."""
        try:
            self.deleteLater()
        except RuntimeError:
            pass

    def redraw(self):
        """Redraw interface."""
        _size = self.size()
        self._pixmap = HPixmap(_size)
        self._pixmap.fill(self.base_col)
        self.update_pixmap(self._pixmap)
        self._label.setPixmap(self._pixmap)

    def update_pixmap(self, pix):
        """Update interface pixmap.

        Args:
            pix (QPixmap): pixmap to update
        """

    def keyPressEvent(self, event):
        """Executed on key press.

        Args:
            event (QEvent): key press event
        """
        if event.text() == 's':
            self._pixmap.save_test()
        elif event.text() in 'qx':
            self.delete()

    def resizeEvent(self, event):
        """Executed on resize.

        Args:
            event (QEvent): resize event
        """
        super(HPixmapUi, self).resizeEvent(event)
        self._label.resize(self.size())
        self.redraw()

    @safe_timer_event
    def timerEvent(self, event):
        """Executed on timer tick.

        Args:
            event (QEvent): timer event
        """
        super(HPixmapUi, self).timerEvent(event)
        self.redraw()
