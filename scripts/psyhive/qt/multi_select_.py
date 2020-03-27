"""Tools for managing a dialog allow the user to select items in a list."""

import os

from psyhive.utils import get_single

from psyhive.qt.wrapper.mgr import QtWidgets
from psyhive.qt.wrapper.widgets import HListWidgetItem
from psyhive.qt.misc import get_application
from psyhive.qt.ui_dialog_3 import HUiDialog3

_DIALOG = None


class _MultiSelectDialog(HUiDialog3):
    """Dialog allowing the user to select items from a list."""

    def __init__(
            self, items, multi, msg, select, title, default, width=None,
            parent=None, labels=None):
        """Constructor.

        Args:
            items (list): list of objects to display
            multi (bool): allow multiple selection (otherwise single
                is applied)
            msg (str): message for dialog
            select (str): label for select button
            title (str): dialog title
            default (any): default value
            width (int): override dialog width
            parent (QDialog): parent dialog
            labels (str list): list of display names for items
                (length must match item list length)
        """
        if labels:
            assert len(labels) == len(items)

        self.items = items
        self.result = None
        self.multi = multi
        self.labels = labels

        _ui_file = "{}/multi_select_.ui".format(os.path.dirname(__file__))
        super(_MultiSelectDialog, self).__init__(
            ui_file=_ui_file, parent=parent, save_settings=False)

        self.setWindowTitle(title)
        self.ui.Message.setText(msg)
        self.ui.Select.setText(select)
        if not self.multi:
            _sel = QtWidgets.QAbstractItemView.SingleSelection
            self.ui.Items.setSelectionMode(_sel)
        if width:
            _h = self.height()
            self.resize(width, _h)
        if default:
            self.ui.Items.select_data(default)

    def init_ui(self):
        """Init ui elements."""
        self._redraw__Items()

    def _redraw__Items(self):
        _items = []
        for _idx, _data_item in enumerate(self.items):
            _label = self.labels[_idx] if self.labels else str(_data_item)
            _qt_item = HListWidgetItem(_label)
            _qt_item.set_data(_data_item)
            _items.append(_qt_item)
        self.ui.Items.set_items(_items)

    def _callback__Select(self):
        self.result = self.ui.Items.selected_data()
        if not self.multi:
            self.result = get_single(self.result)
        self.close()


def multi_select(
        items, msg='Select items:', title="Select", multi=True,
        default=None, select='Select', width=None, pos=None,
        parent=None, labels=None):
    """Raise a dialog requesting selection from a list of items.

    Args:
        items (list): list of objects to display
        msg (str): message for dialog
        title (str): dialog title
        multi (bool): allow multiple selection (default is True)
        default (any): default value
        select (str): label for select button
        width (int): override dialog width
        pos (QPoint): position for dialog
        parent (QDialog): parent dialog
        labels (str list): list of display names for items
            (length must match item list length)
    """
    from psyhive import qt
    global _DIALOG

    if not items:
        raise RuntimeError('No items')
    get_application()

    # Raise dialog
    _DIALOG = _MultiSelectDialog(
        items=items, multi=multi, msg=msg, select=select, title=title,
        width=width, default=default, parent=parent, labels=labels)
    if pos:
        _pos = pos - qt.get_p(_DIALOG.size()/2)
        _DIALOG.move(_pos)
    _DIALOG.exec_()
    if _DIALOG and _DIALOG.result is None:
        raise qt.DialogCancelled

    return _DIALOG and _DIALOG.result
