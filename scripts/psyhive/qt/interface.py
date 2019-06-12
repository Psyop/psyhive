"""Tools for managing qt interfaces."""

import os
import sys
import tempfile
import types

import six

from psyhive import host
from psyhive.utils import (
    wrap_fn, lprint, dprint, abs_path, File, touch, find, dev_mode)

from psyhive.qt.wrapper.mgr import QtWidgets, QtUiTools, QtCore
from psyhive.qt.wrapper.widgets import (
    HCheckBox, HLabel, HTextBrowser, HPushButton, HMenu, HListWidget)
from psyhive.qt.misc import get_pixmap, get_icon, get_p

if not hasattr(sys, 'QT_DIALOG_STACK'):
    sys.QT_DIALOG_STACK = {}

_SETTINGS_DIR = abs_path('{}/psyhive/settings'.format(tempfile.gettempdir()))


class HUiDialog(QtWidgets.QDialog):
    """Base class for any interface."""

    def __init__(
            self, ui_file, catch_error_=True, track_usage_=True,
            dialog_stack_key=None, connect_widgets=True, show=True,
            parent=None, save_settings=True, verbose=0):
        """Constructor.

        Args:
            ui_file (str): path to ui file
            catch_error_ (bool): apply catch error decorator to callbacks
            track_usage_ (bool): apply track usage decorator to callbacks
            dialog_stack_key (str): override dialog stack key
            connect_widgets (bool): connect widget callbacks
            show (bool): show interface
            parent (QDialog): parent dialog
            save_settings (bool): read/write settings on open/close
            verbose (int): print process data
        """
        if not os.path.exists(ui_file):
            raise OSError('Missing ui file '+ui_file)

        # Remove any existing widgets
        _dialog_stack_key = dialog_stack_key or abs_path(ui_file)
        if _dialog_stack_key in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[_dialog_stack_key].delete()
        sys.QT_DIALOG_STACK[_dialog_stack_key] = self

        _parent = parent or _get_default_parent()
        _args = [_parent] if _parent else []
        super(HUiDialog, self).__init__(*_args)

        # Load ui file
        _loader = QtUiTools.QUiLoader()
        _loader.registerCustomWidget(HCheckBox)
        _loader.registerCustomWidget(HLabel)
        _loader.registerCustomWidget(HListWidget)
        _loader.registerCustomWidget(HPushButton)
        _loader.registerCustomWidget(HTextBrowser)
        assert os.path.exists(ui_file)
        self.ui = _loader.load(ui_file, self)
        self._is_widget_ui = type(self.ui) is QtWidgets.QWidget
        if self._is_widget_ui:
            _layout = self.ui.layout()
            if _layout:  # Fix maya margins override
                _layout.setContentsMargins(9, 9, 9, 9)
            self.ui.closeEvent = self.closeEvent
            self.setWindowTitle(self.ui.windowTitle())
        else:
            self.ui.rejected.connect(self.closeEvent)
            if dev_mode() and isinstance(self.ui, QtWidgets.QDialog):
                dprint("WARNING: QDialog is unstable in maya")

        # Setup widgets
        self.widgets = self.read_widgets()
        if connect_widgets:
            self.connect_widgets(
                catch_error_=catch_error_, track_usage_=track_usage_,
                verbose=verbose)

        # Handle settings
        if save_settings:
            _settings_file = abs_path('{}/{}.ini'.format(
                _SETTINGS_DIR, File(ui_file).basename))
            touch(_settings_file)  # Check settings writable
            self.settings = QtCore.QSettings(
                _settings_file, QtCore.QSettings.IniFormat)
            self.read_settings(verbose=verbose)
        else:
            self.settings = None

        self.redraw_ui()

        if show:
            self.show() if self._is_widget_ui else self.ui.show()

    def closeEvent(self, event=None, verbose=0):
        """Triggered on close dialog.

        Args:
            event (QEvent): triggered event
            verbose (int): print process data
        """
        lprint("EXECUTING CLOSE EVENT", verbose=verbose)

        _result = None
        if event:
            _result = QtWidgets.QDialog.closeEvent(self, event)

        if hasattr(self, 'write_settings'):
            self.write_settings()

        return _result

    def resizeEvent(self, event, verbose=0):
        """Triggered by resize.

        Args:
            event (QEvent): triggered event
            verbose (int): print process data
        """
        lprint("RESIZE", self, verbose=verbose)

        _result = super(HUiDialog, self).resizeEvent(event)

        # Fix maya QWidget resize bug
        if self._is_widget_ui:
            self.ui.resize(self.size())

        return _result

    def connect_widgets(
            self, catch_error_=False, track_usage_=True, verbose=0):
        """Connect widgets with redraw/callback methods.

        Only widgets with override types are linked.

        Args:
            catch_error_ (bool): apply catch error decorator to callbacks
            track_usage_ (bool): apply track usage decorator to callbacks
            verbose (int): print process data
        """
        for _widget in self.widgets:

            _name = _widget.objectName()
            lprint('CHECKING', _name, verbose=verbose > 1)

            # Connect callback
            _callback = getattr(self, '_callback__'+_name, None)
            if _callback:
                if isinstance(_widget, QtWidgets.QPushButton):
                    if track_usage_:
                        from psyhive.tools import track_usage
                        _callback = track_usage(_callback)
                    if catch_error_:
                        from psyhive.tools import get_error_catcher
                        _catcher = get_error_catcher(exit_on_error=False)
                        _callback = _catcher(_callback)
                _callback = wrap_fn(_callback)  # To lose args from hook
                lprint(' - CONNECTING', _widget, verbose=verbose)
                for _hook_name in [
                        'clicked',
                        'currentTextChanged',
                        'textChanged',
                ]:
                    _hook = getattr(_widget, _hook_name, None)
                    if _hook:
                        _hook.connect(_callback)

            # Connect context
            _context = getattr(self, '_context__'+_name, None)
            if _context:
                _widget.customContextMenuRequested.connect(
                    _build_context_fn(_context, widget=_widget))
                _widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

            # Connect redraw callback
            _redraw = getattr(self, '_redraw__'+_name, None)
            if _redraw:
                lprint(' - CONNECTING REDRAW', _widget, verbose=verbose)
                _mthd = _build_redraw_method(_redraw)
                _widget.redraw = types.MethodType(_mthd, _widget)

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

    def get_c(self):
        """Get centre point of this interface.

        Returns:
            (QPoint): centre point
        """
        if self._is_widget_ui:
            _dialog = self
        else:
            _dialog = self.ui
        return _dialog.pos() + get_p(_dialog.size()/2)

    def read_settings(self, verbose=0):
        """Read settings from disk.

        Args:
            verbose (int): print process data
        """
        if not self.settings:
            return
        dprint('READ SETTINGS', self.settings.fileName(), verbose=verbose)

        # Apply window settings
        _pos = self.settings.value('window/pos')
        if _pos:
            lprint(' - APPLYING POS', _pos, verbose=verbose)
            self.ui.move(_pos)
        _size = self.settings.value('window/size')
        if _size:
            lprint(' - APPLYING SIZE', _size, verbose=verbose)
            self.ui.resize(_size)

        # Apply widget settings
        for _widget in self.widgets:
            _name = _widget.objectName()
            _val = self.settings.value(_name)
            if _val is None:
                continue
            lprint(' - APPLY', _name, _val, verbose=verbose)
            if isinstance(_widget, QtWidgets.QLineEdit):
                _widget.setText(_val)
            elif isinstance(_widget, (
                    QtWidgets.QRadioButton,
                    QtWidgets.QCheckBox)):
                if isinstance(_val, six.string_types):
                    _val = {'true': True, 'false': False}[_val]
                if isinstance(_val, bool):
                    _widget.setChecked(_val)
                else:
                    print ' - FAILED TO APPLY:', _widget, _val, type(_val)
            elif isinstance(_widget, QtWidgets.QPushButton):
                if _val:
                    _widget.setChecked(_val)
            elif isinstance(_widget, QtWidgets.QListWidget):
                for _row in range(_widget.count()):
                    _item = _widget.item(_row)
                    _item.setSelected(_item.text() in _val)
            elif isinstance(_widget, QtWidgets.QTabWidget):
                try:
                    _widget.setCurrentIndex(_val)
                except TypeError:
                    print ' - FAILED TO APPLY TAB', _val
            elif isinstance(_widget, QtWidgets.QSplitter):
                _val = [int(_item) for _item in _val]
                print 'SET SIZE', _val
                _widget.setSizes(_val)
            else:
                raise ValueError(_widget)

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
        _icon = get_icon(_pix)
        self.setWindowIcon(_pix)
        self.ui.setWindowIcon(_pix)

    def write_settings(self, verbose=0):
        """Write settings to disk.

        Args:
            verbose (int): print process data
        """
        if not self.settings:
            return
        dprint('WRITING SETTINGS', self.settings.fileName(), verbose=verbose)

        for _widget in self.widgets:
            if isinstance(_widget, QtWidgets.QLineEdit):
                _val = _widget.text()
            elif isinstance(_widget, (
                    QtWidgets.QRadioButton,
                    QtWidgets.QCheckBox)):
                _val = _widget.isChecked()
            elif isinstance(_widget, QtWidgets.QListWidget):
                _val = [
                    str(_item.text()) for _item in _widget.selectedItems()]
            elif isinstance(_widget, QtWidgets.QTabWidget):
                _val = _widget.currentIndex()
            elif isinstance(_widget, QtWidgets.QSplitter):
                _val = _widget.sizes()
            else:
                continue
            lprint(' - SAVING', _widget.objectName(), _val, verbose=verbose)
            self.settings.setValue(_widget.objectName(), _val)

        self.settings.setValue('window/pos', self.ui.pos())
        lprint(' - SAVING POS', self.ui.pos(), verbose=verbose)
        self.settings.setValue('window/size', self.ui.size())
        lprint(' - SAVING SIZE', self.ui.size(), verbose=verbose)


def _build_context_fn(callback, widget):
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


def _build_redraw_method(redraw):
    """Build redraw method from the given redraw function.

    When the method called, signals are blocked from the widget, the
    redraw is executed, signals are unblocked and the the changed
    signal is triggered.

    Args:
        redraw (fn): redraw function
    """

    def _redraw_method(widget):
        widget.blockSignals(True)
        redraw(widget=widget)
        widget.blockSignals(False)

        # Emit changed signal
        for _name in ['itemSelectionChanged', 'stateChanged']:
            if not hasattr(widget, _name):
                continue
            _signal = getattr(widget, _name)
            _signal.emit()
            break

    return _redraw_method


def close_all_interfaces():
    """Close all mayanged psyhive dialogs.

    This is used to avoid instability when reloading modules.
    """
    for _key, _dialog in sys.QT_DIALOG_STACK.items():
        print 'CLOSING', _dialog
        _dialog.delete()
        del sys.QT_DIALOG_STACK[_key]


def _get_default_parent():
    """Get default parent based on current dcc.

    Returns:
        (QWidget): default parent
    """
    _parent = None
    if host.NAME == 'maya':
        from maya_psyhive import ui
        _parent = ui.get_main_window_ptr()
    return _parent


def get_list_redrawer(default_selection='first'):
    """Build a decorator for redrawing lists.

    This will empty the list before redrawing, and attempt to maintain
    the current selection. If nothing is selected, it will then apply the
    default selection behaviour.

    Args:
        default_selection (str): default selection policy (first or all)

    Returns:
        (fn): redraw decorator
    """

    def _list_redrawer(func):

        def _redraw_list(self, widget):

            _sel = widget.selected_text()
            widget.clear()

            func(self, widget)

            # Apply selection
            if not widget.selectedItems():
                widget.select_text(_sel)
            if not widget.selectedItems():
                if default_selection == 'first':
                    widget.setCurrentRow(0)
                elif default_selection == 'all':
                    widget.selectAll()
                else:
                    raise ValueError(default_selection)

        return _redraw_list

    return _list_redrawer


def list_redrawer(func):
    """Decorator to redraw a list widget.

    Args:
        func (fn): redraw function to decorate

    Returns:
        (fn): decorated function
    """
    return get_list_redrawer()(func)


def reset_interface_settings():
    """Reset interface settings."""
    dprint('RESET SETTINGS', _SETTINGS_DIR)
    for _ini in find(_SETTINGS_DIR, depth=1, type_='f', extn='ini'):
        print ' - REMOVING', _ini
        os.remove(_ini)
