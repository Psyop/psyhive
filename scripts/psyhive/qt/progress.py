"""Tools for managing the progress bar dialog."""

import collections

from psyhive.utils import get_plural

from psyhive.qt.misc import get_application
from psyhive.qt.mgr import QtWidgets
from psyhive.qt.widgets import HProgressBar
from psyhive.qt.dialog import DialogCancelled


class _CancelIteration(StopIteration, DialogCancelled):
    """Raised when in iteration is cancelled by closing the progress bar."""


class ProgressBar(QtWidgets.QDialog):
    """Simple dialog for showing progress of an interation."""

    def __init__(self, items, title=None, col=None, show=True):
        """Constructor.

        Args:
            items (list): list of items to iterate
            title (str): title for interface
            col (str): progress bar colour
            show (bool): show the dialog
        """
        _items = items
        if isinstance(_items, (enumerate, collections.Iterable)):
            _items = list(_items)

        self.items = _items
        self.counter = 0

        super(ProgressBar, self).__init__()

        _title = (title or 'Processing {:d} items').format(
            len(self.items), get_plural(self.items))
        self.setWindowTitle(_title)
        self.resize(408, 54)

        # Build ui
        self.grid_lyt = QtWidgets.QGridLayout(self)
        self.progress_bar = HProgressBar(self)
        _size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        _size_policy.setHorizontalStretch(0)
        _size_policy.setVerticalStretch(0)
        _size_policy.setHeightForWidth(
            self.progress_bar.sizePolicy().hasHeightForWidth())
        self.progress_bar.setSizePolicy(_size_policy)
        self.progress_bar.setProperty("value", 0)
        self.grid_lyt.addWidget(self.progress_bar, 0, 0, 1, 1)
        if col:
            self.progress_bar.set_col(col)

        self._hidden = True
        if show:
            self.show()

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.items)

    def __next__(self):

        if not self._hidden and not self.isVisible():
            raise _CancelIteration

        _pc = 100.0 * self.counter / len(self.items)
        self.progress_bar.setValue(_pc)
        get_application().processEvents()

        self.counter += 1
        try:
            _result = self.items[self.counter-1]
        except IndexError:
            self.close()
            raise StopIteration

        return _result

    next = __next__
