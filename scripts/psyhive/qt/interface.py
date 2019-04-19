"""Tools for managing qt interfaces."""

import tempfile
import os
import sys

from psyhive import host
from psyhive.utils import wrap_fn, lprint, dprint

from psyhive.qt.mgr import QtWidgets, QtUiTools, QtCore
from psyhive.qt.widgets import HLabel, HTextBrowser, HPushButton, HMenu
from psyhive.qt.misc import get_pixmap

if not hasattr(sys, 'QT_DIALOG_STACK'):
    sys.QT_DIALOG_STACK = {}


class HUiDialog(QtWidgets.QDialog):
    """Base class for any interface."""

    def __init__(
            self, ui_file, catch_error_=True, dialog_stack_key=None,
            verbose=0):
        """Constructor.

        Args:
            ui_file (str): path to ui file
            catch_error_ (bool): apply catch error decorator to callbacks
            dialog_stack_key (str): override dialog stack key
            verbose (int): print process data
        """
        if not os.path.exists(ui_file):
            raise OSError('Missing ui file '+ui_file)

        # Remove any existing widgets
        _dialog_stack_key = dialog_stack_key or ui_file
        if _dialog_stack_key in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[_dialog_stack_key].delete()
        sys.QT_DIALOG_STACK[_dialog_stack_key] = self

        super(HUiDialog, self).__init__()

        self.set_parenting()

        # Load ui file
        _loader = QtUiTools.QUiLoader()
        _loader.registerCustomWidget(HLabel)
        _loader.registerCustomWidget(HTextBrowser)
        _loader.registerCustomWidget(HPushButton)
        self.ui = _loader.load(ui_file, self)

        # Setup widgets
        self.widgets = self.read_widgets()
        self.connect_widgets(catch_error_=catch_error_, verbose=verbose)

        # Handle settings
        self.settings_file = '{}/psyhive/{}.ini'.format(
            tempfile.gettempdir(), _dialog_stack_key)
        self.settings = QtCore.QSettings(
            self.settings_file, QtCore.QSettings.IniFormat)
        self.read_settings()

        self.redraw_ui()
        self.ui.show()

    def closeEvent(self, event):
        """Triggered on close dialog.

        Args:
            event (QEvent): triggered event
        """
        _result = QtWidgets.QDialog.closeEvent(self, event)
        if hasattr(self, 'write_settings'):
            self.write_settings()
        return _result

    def connect_widgets(self, catch_error_=False, verbose=0):
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
                    from psyhive.tools import get_error_catcher
                    _catcher = get_error_catcher(exit_on_error=False)
                    _callback = _catcher(_callback)
                _callback = wrap_fn(_callback)  # To lose args from hook
                lprint(' - CONNECTING', _widget, verbose=verbose)
                for _hook_name in ['clicked', 'textChanged']:
                    _hook = getattr(_widget, _hook_name, None)
                    if _hook:
                        _hook.connect(_callback)

            # Connect context
            _context = getattr(self, '_context__'+_name, None)
            if _context:
                _widget.customContextMenuRequested.connect(
                    _get_context_fn(_context, widget=_widget))
                _widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

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
                self.close,
                self.deleteLater,
        ]:
            if not _fn:
                continue
            try:
                _fn()
            except Exception:
                lprint('FAILED TO EXEC', _fn, verbose=verbose)

    def read_settings(self, verbose=0):
        """Read settings from disk.

        Args:
            verbose (int): print process data
        """
        dprint('READ SETTINGS', verbose=verbose)

        # Apply widget settings
        for _widget in self.widgets:
            _name = _widget.objectName()
            _val = self.settings.value(_name)
            if not _val:
                continue
            lprint(' - APPLY', _name, _val, verbose=verbose)
            if isinstance(_widget, QtWidgets.QLineEdit):
                _widget.setText(_val)
            elif isinstance(_widget, (
                    QtWidgets.QRadioButton,
                    QtWidgets.QCheckBox)):
                _widget.setChecked(_val)
            else:
                raise ValueError(_widget)

        # Apply window settings
        _pos = self.settings.value('window/pos')
        if _pos:
            lprint(' - APPLYING POS', _pos, verbose=verbose)
            self.ui.move(_pos)

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

    def set_icon(self, icon):
        """Set icon for this interface.

        Args:
            icon (str|QPixmap): icon to apply
        """
        _pix = get_pixmap(icon)
        self.setWindowIcon(_pix)

    def set_parenting(self):
        """Set parenting for host application."""
        if host.NAME == 'maya':
            from maya_psyhive import ui
            _maya_win = ui.get_main_window_ptr()
            self.setParent(_maya_win, QtCore.Qt.WindowStaysOnTopHint)

    def write_settings(self, verbose=0):
        """Write settings to disk.

        Args:
            verbose (int): print process data
        """
        dprint('SAVING SETTINGS', self.settings.fileName(), verbose=verbose)

        for _widget in self.widgets:
            if isinstance(_widget, QtWidgets.QLineEdit):
                _val = _widget.text()
            elif isinstance(_widget, (
                    QtWidgets.QRadioButton,
                    QtWidgets.QCheckBox)):
                _val = _widget.isChecked()
            else:
                continue
            lprint(' - SAVING', _widget.objectName(), _val, verbose=verbose)
            self.settings.setValue(_widget.objectName(), _val)

        self.settings.setValue('window/pos', self.ui.pos())
        lprint(' - SAVING POS', self.ui.pos(), verbose=verbose)


def _get_context_fn(callback, widget):
    """Build function connect widget right-click to the given callback.

    Args:
        callback (fn): context menu callback to connect to
        widget (QWidget): widget to apply callback to
    """

    def _context_fn(pos):
        _menu = HMenu(widget)
        callback(_menu)
        _menu.exec_(widget.mapToGlobal(pos))

    return _context_fn


def close_all_dialogs():
    """Close all mayanged psyhive dialogs.

    This is used to avoid instability when reloading modules.
    """
    for _dialog in sys.QT_DIALOG_STACK.values():
        print 'CLOSING', _dialog
        _dialog.delete()
