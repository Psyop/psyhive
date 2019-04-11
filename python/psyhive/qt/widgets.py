"""Qt widget overrides."""

from psyhive.qt.mgr import QtWidgets, QtGui
from psyhive.qt.misc import get_col


class HWidgetBase(object):
    """Base class for any override widget."""

    def __init__(self):
        """Constructor."""
        self.influences = set()

    def redraw(self):
        """To be implemented in subclass to populate widget."""

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.objectName())


class HLabel(QtWidgets.QLabel, HWidgetBase):
    """Override for QLabel widget."""
    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(HLabel, self).__init__(*args, **kwargs)
        HWidgetBase.__init__(self)


class HProgressBar(QtWidgets.QProgressBar, HWidgetBase):
    """Override for QProgressBar object."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(HProgressBar, self).__init__(*args, **kwargs)
        HWidgetBase.__init__(self)

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


class HTextBrowser(QtWidgets.QTextBrowser, HWidgetBase):
    """Override for QTextBrowser object."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(HTextBrowser, self).__init__(*args, **kwargs)
        HWidgetBase.__init__(self)
