"""Tools for managing a dialog allow the user to select items in a list."""

import os

from psyhive.utils import get_single

from psyhive.qt.wrapper.mgr import QtWidgets
from psyhive.qt.wrapper.widgets import HListWidgetItem
from psyhive.qt.misc import get_application
from psyhive.qt.interface import HUiDialog, list_redrawer


class _MultiSelectDialog(HUiDialog):
    """Dialog allowing the user to select items from a list."""

    def __init__(
            self, items, multi, msg, select, title, default, width=None):
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
        """
        self.items = items
        self.result = None
        self.multi = multi

        _ui_file = "{}/multi_select_.ui".format(os.path.dirname(__file__))
        super(_MultiSelectDialog, self).__init__(ui_file=_ui_file)

        self.ui.setWindowTitle(title)
        self.ui.message.setText(msg)
        self.ui.select.setText(select)
        if not self.multi:
            _sel = QtWidgets.QAbstractItemView.SingleSelection
            self.ui.items.setSelectionMode(_sel)
        if width:
            _h = self.height()
            self.resize(width, _h)
        if default:
            self.ui.items.select_data(default)

    @list_redrawer
    def _redraw__items(self, widget):
        for _data_item in self.items:
            _qt_item = HListWidgetItem(str(_data_item))
            _qt_item.set_data(_data_item)
            widget.addItem(_qt_item)

    def _callback__select(self):
        self.result = self.ui.items.selected_data()
        if not self.multi:
            self.result = get_single(self.result)
        self.ui.close()


def multi_select(
        items, msg='Select items:', title="Select", multi=True,
        default=None, select='Select', width=None, pos=None):
    """Raise a dialog requesting selection from a list of items.

    Args:
        items (list): list of objects to display
        msg (str): message for dialog
        title (str): dialog title
        multi (bool): allow multiple selection (otherwise single
            is applied)
        default (any): default value
        select (str): label for select button
        width (int): override dialog width
        pos (QPoint): position for dialog
    """
    from psyhive import qt

    if not items:
        raise RuntimeError('No items')
    get_application()

    # Raise dialog
    _dialog = _MultiSelectDialog(
        items=items, multi=multi, msg=msg, select=select, title=title,
        width=width, default=default)
    if pos:
        _pos = pos - qt.get_p(_dialog.ui.size()/2)
        _dialog.ui.move(_pos)
    _dialog.ui.exec_()
    if _dialog.result is None:
        raise qt.DialogCancelled

    return _dialog.result
