"""Tools for managing the progress bar dialog."""

import collections
import copy

from psyhive.utils import get_plural, check_heart, lprint

from psyhive.qt.misc import get_application, get_p
from psyhive.qt.wrapper import QtWidgets, Y_AXIS, HProgressBar

_PROGRESS_BARS = []


def _get_next_pos(title, stack_key):
    """Get position for next progress bar.

    This checks the existing progress bars, removing any ones which have
    expired or have the same title as this bar, and then returns a position
    below the last bar.

    Args:
        title (str): title of progress bar being positioned
        stack_key (str): identifier for this progress bar
    """

    # Flush out unused bars
    for _bar in copy.copy(_PROGRESS_BARS):
        if (
                not _bar.isVisible() or
                _bar.windowTitle() == title or
                _bar.stack_key == stack_key):
            _PROGRESS_BARS.remove(_bar)

    if not _PROGRESS_BARS:
        return None

    return _PROGRESS_BARS[-1].pos() + Y_AXIS*100


class ProgressBar(QtWidgets.QDialog):
    """Simple dialog for showing progress of an interation."""

    def __init__(
            self, items, title=None, col=None, show=True, pos=None,
            parent=None, stack_key='progress'):
        """Constructor.

        Args:
            items (list): list of items to iterate
            title (str): title for interface
            col (str): progress bar colour
            show (bool): show the dialog
            pos (QPoint): override progress bar position (applied to centre)
            parent (QDialog): parent dialog
            stack_key (str): override identifier for this dialog - if an
                existing progress bar has the same stack key then this
                will replace it
        """
        _items = items
        if isinstance(_items, (enumerate, collections.Iterable)):
            _items = list(_items)

        self.stack_key = stack_key
        self.items = _items
        self.counter = 0

        _args = [parent] if parent else []
        super(ProgressBar, self).__init__(*_args)

        _title = (title or 'Processing {:d} item{}').format(
            len(self.items), get_plural(self.items))
        self.setWindowTitle(_title)
        self.resize(408, 54)

        if pos:
            _pos = pos - get_p(self.size())/2
        else:
            _pos = _get_next_pos(title=_title, stack_key=stack_key)
        if _pos:
            self.move(_pos)

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

        self._hidden = not show
        if show:
            self.show()
        _PROGRESS_BARS.append(self)

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.items)

    def __next__(self, verbose=0):

        from psyhive import qt

        lprint('ITERATING', self.isVisible(), verbose=verbose)
        check_heart()

        if not self._hidden and not self.isVisible():
            raise qt.DialogCancelled

        _pc = 100.0 * self.counter / max(len(self.items), 1)
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
