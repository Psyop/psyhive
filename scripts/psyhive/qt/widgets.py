"""Qt widget overrides."""

from psyhive.qt.mgr import QtWidgets, QtGui, QtCore
from psyhive.qt.misc import get_col, get_pixmap


def _dummy():
    """Function which does nothing - use for QMenu label."""


class HWidgetBase(object):
    """Base class for any override widget."""

    def redraw(self):
        """To be implemented in subclass to populate widget."""

    def set_pixmap(self, pixmap):
        """Set pixmap for this widget.

        Args:
            pixmap (str|QPixmap): pixmap to apply
        """
        self.setPixmap(get_pixmap(pixmap))

    def set_icon(self, pixmap):
        """Set icon for this widget.

        Args:
            pixmap (str|QPixmap): pixmap to apply
        """
        _icon = QtGui.QIcon(get_pixmap(pixmap))
        self.setIcon(_icon)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.objectName())


class HCheckBox(QtWidgets.QCheckBox, HWidgetBase):
    """Override for QCheckBox widget."""


class HLabel(QtWidgets.QLabel, HWidgetBase):
    """Override for QLabel widget."""


class HMenu(QtWidgets.QMenu, HWidgetBase):
    """Override for QMenu widget."""

    def add_action(self, text, func, icon=None):
        """Add an action to the menu.

        Args:
            text (str): action text
            func (fn): action function
            icon (str|QPixmap): action icon
        """
        _args = [text, func]
        if icon:
            _args = [get_pixmap(icon)] + _args
        return self.addAction(*_args)

    def add_label(self, text, icon=None):
        """Add label to the menu.

        This is a disabled piece of text.

        Args:
            text (str): display text
            icon (str|QPixmap): icon
        """
        _action = self.add_action(text=text, func=_dummy, icon=icon)
        _action.setEnabled(0)
        return _action


class HProgressBar(QtWidgets.QProgressBar, HWidgetBase):
    """Override for QProgressBar object."""

    def set_col(self, col):
        """Set colour for this progress bar.

        Args:
            col (str): colour to apply
        """
        _col = get_col(col)
        _palette = QtGui.QPalette()
        _brush = QtGui.QBrush(_col)
        for _state in [
                QtGui.QPalette.Active, QtGui.QPalette.Inactive]:
            _palette.setBrush(
                _state, QtGui.QPalette.Highlight, _brush)
        self.setPalette(_palette)


class HPushButton(QtWidgets.QPushButton, HWidgetBase):
    """Override for QPushButton object."""


class HTextBrowser(QtWidgets.QTextBrowser, HWidgetBase):
    """Override for QTextBrowser object."""


class HTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """Override for QTreeWidgetItem object."""

    _col = None

    def __init__(self, text, col=None, data=None):
        """Constructor.

        Args:
            text (str): display text
            col (str): text colour
            data (any): data to store with item
        """
        self._col = col or self._col
        super(HTreeWidgetItem, self).__init__()
        self.setText(0, text)
        if self._col:
            _brush = QtGui.QBrush(QtGui.QColor(self._col))
            self.setForeground(0, _brush)
        if data:
            self.setData(0, QtCore.Qt.UserRole, data)

    def get_data(self):
        """Get retrieve data from this item."""
        return self.data(0, QtCore.Qt.UserRole)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__.strip('_'), self.text(0))
