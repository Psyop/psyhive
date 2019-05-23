"""Tools for managing a dialog allow the user to select items in a list."""

import os

from psyhive.utils import get_single

from psyhive.qt.wrapper.mgr import QtWidgets
from psyhive.qt.wrapper.widgets import HListWidgetItem
from psyhive.qt.misc import get_application
from psyhive.qt.interface import HUiDialog, list_redrawer

_DIALOG = None


class _MultiSelectDialog(HUiDialog):
    """Dialog allowing the user to select items from a list."""

    def __init__(
            self, items, multi, msg, select, title, default, width=None,
            parent=None):
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
        """
        self.items = items
        self.result = None
        self.multi = multi

        _ui_file = "{}/multi_select_.ui".format(os.path.dirname(__file__))
        super(_MultiSelectDialog, self).__init__(
            ui_file=_ui_file, parent=parent, save_settings=False)

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
        self.close()


def multi_select(
        items, msg='Select items:', title="Select", multi=True,
        default=None, select='Select', width=None, pos=None,
        parent=None):
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
        parent (QDialog): parent dialog
    """
    from psyhive import qt
    global _DIALOG

    if not items:
        raise RuntimeError('No items')
    get_application()

    # Raise dialog
    _DIALOG = _MultiSelectDialog(
        items=items, multi=multi, msg=msg, select=select, title=title,
        width=width, default=default, parent=parent)
    if pos:
        _pos = pos - qt.get_p(_DIALOG.size()/2)
        _DIALOG.move(_pos)
    _DIALOG.exec_()
    if _DIALOG.result is None:
        raise qt.DialogCancelled

    return _DIALOG.result
