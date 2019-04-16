"""Tools for managing qt interfaces."""

import os
import sys

from psyhive.tools import catch_error
from psyhive.qt.mgr import QtWidgets, QtUiTools
from psyhive.qt.widgets import HLabel, HTextBrowser
from psyhive.utils import wrap_fn, lprint

if not hasattr(sys, 'QT_DIALOG_STACK'):
    sys.QT_DIALOG_STACK = {}


class HUiDialog(QtWidgets.QDialog):
    """Base class for any interface."""

    def __init__(self, ui_file, verbose=0):
        """Constructor.

        Args:
            ui_file (str): path to ui file
            verbose (int): print process data
        """
        if not os.path.exists(ui_file):
            raise OSError('Missing ui file '+ui_file)

        # Remove any existing widgets
        _dialog_stack_key = ui_file
        if _dialog_stack_key in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[_dialog_stack_key].delete()
        sys.QT_DIALOG_STACK[_dialog_stack_key] = self

        super(HUiDialog, self).__init__()

        # Load ui file
        _loader = QtUiTools.QUiLoader()
        _loader.registerCustomWidget(HLabel)
        _loader.registerCustomWidget(HTextBrowser)
        self.ui = _loader.load(ui_file, self)

        # Setup widgets
        self.widgets = self.read_widgets()
        self.connect_widgets(verbose=verbose)

        self.redraw_ui()
        self.ui.show()

    def connect_widgets(self, catch_error_=True, verbose=0):
        """Connect widgets with redraw/callback methods.

        Only widgets with override types are linked.

        Args:
            catch_error_ (bool): apply catch error decorator to callbacks
            verbose (int): print process data
        """
        for _widget in self.widgets:

            _name = _widget.objectName()
            lprint('CHECKING', _name, verbose=verbose)

            # Connect callback
            _callback = getattr(self, '_callback__'+_name, None)
            if _callback:
                if catch_error_:
                    _callback = catch_error(_callback)
                lprint(' - CONNECTING', _widget, verbose=verbose)
                for _hook_name in ['clicked']:
                    _hook = getattr(_widget, _hook_name, None)
                    if _hook:
                        _hook.connect(_callback)

            # Connect draw callback
            _redraw = getattr(self, '_redraw__'+_name, None)
            if _redraw:
                _widget.redraw = wrap_fn(_redraw, widget=_widget)

    def delete(self, verbose=0):
        """Delete this dialog.

        Args:
            verbose (int): print process data
        """
        lprint('DELETING', self, verbose=verbose)
        for _fn in [
                self.ui.close if hasattr(self, 'ui') else None,
                self.ui.deleteLater if hasattr(self, 'ui') else None,
                self.deleteLater,
        ]:
            if not _fn:
                continue
            try:
                _fn()
            except Exception:
                lprint('FAILED TO EXEC', _fn, verbose=verbose)

    def read_widgets(self):
        """Read widgets with overidden types from ui object."""
        _widgets = []
        for _widget in self.ui.findChildren(QtWidgets.QWidget):
            _name = _widget.objectName()
            _widgets.append(_widget)
            setattr(self.ui, _name, _widget)
        return _widgets

    def redraw_ui(self, verbose=0):
        """Redraw widgets that need updating.

        Args:
            verbose (int): print process data
        """
        _widgets = self.widgets

        # Redraw widgets
        lprint(
            ' - REDRAWING {:d} WIDGETS'.format(len(_widgets)),
            verbose=verbose)
        for _widget in _widgets:
            _redraw = getattr(_widget, 'redraw', None)
            if _redraw:
                _redraw()


def close_all_dialogs():
    """Close all mayanged psyhive dialogs.

    This is used to avoid instability when reloading modules.
    """
    for _dialog in sys.QT_DIALOG_STACK.values():
        print 'CLOSING', _dialog
        _dialog.delete()
