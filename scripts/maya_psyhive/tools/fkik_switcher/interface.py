"""Tools for managing the fk/ik interface."""

import os

from maya import cmds

from psyhive import qt, icons
from psyhive.tools import HandledError
from psyhive.utils import abs_path, wrap_fn

from maya_psyhive.tools.fkik_switcher import system

_DIALOG = None
_UI_FILE = abs_path('fkik_switcher.ui', root=os.path.dirname(__file__))
ICON = icons.EMOJI.find('Left-Right Arrow')


class _NoSystemSelected(HandledError):
    """Raised when no FK/IK system is selected."""

    def __init__(self, msg):
        """Constructor.

        Args:
            msg (str): error message
        """
        super(_NoSystemSelected, self).__init__(msg=msg)


class _FkIkSwitcherUi(qt.HUiDialog):
    """Interface for FK/IK switcher."""
    def __init__(self):
        """Constructor."""
        super(_FkIkSwitcherUi, self).__init__(ui_file=_UI_FILE)
        self.set_icon(ICON)

    def _callback__fk_to_ik(self):
        print 'FK -> IK'
        self._execute_switch(mode='fk_to_ik')

    def _callback__ik_to_fk(self):
        print 'IK -> FK'
        self._execute_switch(mode='ik_to_fk')

    def _callback__keyframe(self):
        _system = system.get_selected_system(error=HandledError)
        cmds.setKeyframe(_system.get_key_attrs())

    def _context__keyframe(self, menu):
        menu.setStyleSheet('background-color:DimGrey; color:white')
        try:
            _system = system.get_selected_system()
        except ValueError as _exc:
            menu.add_label(_exc.message)
        else:
            _nodes = _system.get_ctrls()
            menu.add_action('Select nodes', wrap_fn(cmds.select, _nodes))

    def _execute_switch(self, mode):
        """Execute switch ik/fk mode.

        Args:
            mode (str): transition to make
        """
        _system = system.get_selected_system(error=HandledError)
        _system.exec_switch_and_key(
            switch_mode=mode,
            switch_key=self.ui.switch_key.isChecked(),
            key_mode=self._read_key_mode())

    def _read_key_mode(self):
        """Read current key mode from radio buttons."""
        for _name in ['none', 'frame', 'timeline']:
            _elem = getattr(self.ui, 'key_'+_name)
            if _elem.isChecked():
                return _name
        raise ValueError("Failed to read key mode")


def launch_interface():
    """Launch FK/IK switcher interface."""
    global _DIALOG
    _DIALOG = _FkIkSwitcherUi()
