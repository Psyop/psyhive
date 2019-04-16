"""Tools for managing the fk/ik interface."""

import os

from psyhive import qt
from psyhive.utils import abs_path

from maya_psyhive.tools.fkik_switcher import system

_DIALOG = None
_UI_FILE = abs_path('fkik_switcher.ui', root=os.path.dirname(__file__))


class _FkIkSwitcherUi(qt.HUiDialog):
    """Interface for FK/IK switcher."""
    def __init__(self):
        """Constructor."""
        super(_FkIkSwitcherUi, self).__init__(ui_file=_UI_FILE)

    def _read_key_mode(self):
        """Read current key mode from radio buttons."""
        for _name in ['none', 'on_switch', 'prev', 'over_range']:
            _elem = getattr(self.ui, 'key_'+_name)
            if _elem.isChecked():
                return _name

        raise ValueError

    def _callback__fk_to_ik(self):
        print 'FK -> IK'
        self._execute_switch(mode='fk_to_ik')

    def _callback__ik_to_fk(self):
        print 'IK -> FK'
        self._execute_switch(mode='ik_to_fk')

    def _execute_switch(self, mode):
        """Execute switch ik/fk mode.

        Args:
            mode (str): transition to make
        """
        _system = system.get_selected_system()
        _key_mode = self._read_key_mode()
        _fn = getattr(_system, 'apply_'+mode)

        print 'APPLYING', _fn, _key_mode


def launch_interface():
    """Launch FK/IK switcher interface."""
    global _DIALOG
    _DIALOG = _FkIkSwitcherUi()
