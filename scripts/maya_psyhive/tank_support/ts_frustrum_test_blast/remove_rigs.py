"""Tools for allowing the user to choose rigs to remove from the scene."""

import os

from maya import cmds

from psyhive import qt
from psyhive.utils import abs_path, get_plural

_DIALOG = None


class _RemoveRigsUi(qt.HUiDialog3):
    """Interface for user to choose rigs to remove."""

    def __init__(self, rigs):
        """Constructor.

        Args:
            rigs (FileRef): list of rigs outside frustrum
        """
        self.rigs = rigs
        _ui_file = abs_path('remove_rigs.ui', root=os.path.dirname(__file__))

        super(_RemoveRigsUi, self).__init__(_ui_file, save_settings=False)

    def _redraw__List(self):

        self.ui.List.clear()
        for _rig in self.rigs:
            _item = qt.HListWidgetItem(_rig.namespace)
            _item.set_data(_rig)
            self.ui.List.addItem(_item)

    def _redraw__Remove(self):
        _to_remove = self.ui.List.selected_data()
        self.ui.Remove.setText('Remove {:d} rig{}'.format(
            len(_to_remove), get_plural(_to_remove)))
        self.ui.Remove.setEnabled(bool(_to_remove))

    def _callback__Select(self):
        _to_remove = self.ui.List.selected_data()
        cmds.select([_rig.get_node('cRoot') for _rig in _to_remove])

    def _callback__Continue(self):
        self.close()

    def _callback__Remove(self):
        _to_remove = self.ui.List.selected_data()
        for _rig in qt.ProgressBar(
                _to_remove, "Removing {:d} rig{}", col='IndianRed'):
            _rig.remove(force=True)
        cmds.refresh()
        self.close()


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
