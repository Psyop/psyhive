"""Tools for allowing the user to choose rigs to remove from the scene."""

import os

from maya import cmds

from psyhive import qt, deprecate
from psyhive.utils import abs_path, get_plural

_DIALOG = None


class _RemoveRigsUi(qt.HUiDialog):
    """Interface for user to choose rigs to remove."""

    def __init__(self, rigs):
        """Constructor.

        Args:
            rigs (FileRef): list of rigs outside frustrum
        """
        self.rigs = rigs
        _ui_file = abs_path('remove_rigs.ui', root=os.path.dirname(__file__))
        super(_RemoveRigsUi, self).__init__(_ui_file, save_settings=False)

        self.ui.list.itemSelectionChanged.connect(self.ui.remove.redraw)

    @qt.get_list_redrawer(default_selection='all')
    def _redraw__list(self, widget):
        for _rig in self.rigs:
            _item = qt.HListWidgetItem(_rig.namespace)
            _item.set_data(_rig)
            widget.addItem(_item)

    def _redraw__remove(self, widget):
        _to_remove = self.ui.list.selected_data()
        widget.setText('Remove {:d} rig{}'.format(
            len(_to_remove), get_plural(_to_remove)))
        widget.setEnabled(bool(_to_remove))

    def _callback__select(self):
        _to_remove = self.ui.list.selected_data()
        cmds.select([_rig.get_node('cRoot') for _rig in _to_remove])

    def _callback__continue_(self):
        self.close()

    def _callback__remove(self):
        _to_remove = self.ui.list.selected_data()
        for _rig in qt.ProgressBar(
                _to_remove, "Removing {:d} rig{}", col='IndianRed'):
            _rig.remove(force=True)
        cmds.refresh()
        self.close()


@deprecate.deprecate_func('19/03/20 Use maya_psyhive.tank_support module')
def launch(rigs, exec_=True):
    """Launch interface for removing rigs.

    Args:
        rigs (FileRef): rigs outside frustrum
        exec_ (bool): exec dialog

    Returns:
        (_RemoveRigsUi): dialog instance
    """
    global _DIALOG
    _DIALOG = _RemoveRigsUi(rigs=rigs)
    if exec_:
        _DIALOG.exec_()
    return _DIALOG
