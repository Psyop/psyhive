"""Rewrite of qt.HUiDialog.

The first version had a threading issue which made it have issues in
maya - some qt elements were getting garbage collected. This new
version doesn't suffer from that issue.
"""

import os
import sys
import types

import six

from psyhive.utils import lprint, wrap_fn, abs_path, File, dprint

from psyhive.qt.wrapper import QtWidgets, Qt, QtCore
from psyhive.qt.interface import (
    _build_redraw_method, _disable_while_executing, _build_context_fn,
    _SETTINGS_DIR, touch, get_ui_loader)


class HUiDialog2(QtWidgets.QDialog):
    """Dialog based on a ui (qt designer) file."""

    settings = None
    _redraw_sorting = None

    def __init__(self, ui_file, dialog_stack_key=None, save_settings=True,
                 catch_error_=False):
        """Constructor.

        Args:
            ui_file (str): path to ui file
            dialog_stack_key (str): override dialog stack identifier
            save_settings (bool): load/save settings
            catch_error_ (bool): apply error catcher decorator
        """
        from psyhive import host

        self.ui_file = ui_file
        if not os.path.exists(self.ui_file):
            raise OSError('Missing ui file '+self.ui_file)

        self._close_existing_uis(dialog_stack_key=dialog_stack_key)

        super(HUiDialog2, self).__init__(parent=host.get_main_window_ptr())

        self._load_ui()
        self._connect_widgets(catch_error_=catch_error_)
        self.redraw_ui()  # Populate before load settings

        self._init_settings(save_settings=save_settings)

        self.show()

    def _close_existing_uis(self, dialog_stack_key):
        """Close existing interfaces with this identifer.

        Normally this is the ui file path.

        Args:
            dialog_stack_key (str): override dialog stack identifier
        """
        _dialog_stack_key = dialog_stack_key or abs_path(self.ui_file)
        if _dialog_stack_key in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[_dialog_stack_key].delete()
        sys.QT_DIALOG_STACK[_dialog_stack_key] = self

    def _load_ui(self):
        """Load interface elements from ui file."""
        _loader = get_ui_loader()
        self.ui = _loader.load(self.ui_file)
        self.setLayout(self.ui.layout())
        self.ui.setParent(self)

        _title = self.ui.windowTitle()
        if _title:
            self.setWindowTitle(_title)

        self.ui.close()

    def _init_settings(self, save_settings):
        """Initiate settings object and read any existing values.

        Args:
            save_settings (bool): load/save settings
        """
        if not save_settings:
            return

        _settings_file = abs_path('{}/{}.ini'.format(
            _SETTINGS_DIR, File(self.ui_file).basename))
        touch(_settings_file)  # Check settings writable
        self.settings = QtCore.QSettings(
            _settings_file, QtCore.QSettings.IniFormat)
        self.read_settings()

    def _connect_widgets(self, catch_error_=True):
        """Connect ui widgets to callbacks.

        Args:
            catch_error_ (bool): apply error catcher decorator
        """
        for _widget in self.findChildren(QtWidgets.QWidget):
            self._connect_widget(_widget, catch_error_=catch_error_)

    def _connect_widget(
            self, widget, track_usage_=True, catch_error_=True,
            disable_btns_on_exec=True, verbose=0):
        """Connect a widget to callbacks on the parent object.

        Args:
            widget (QWidget): widget to connect
            track_usage_ (bool): apply track usage decorator
            catch_error_ (bool): apply error catcher decorator
            disable_btns_on_exec (bool): disable push buttons while
                executing (this can interfere with custom on the
                fly enabling/disabling)
            verbose (int): print process data
        """
        _name = widget.objectName()

        # See if this element needs connecting
        if not _name:
            return
        _callback = getattr(self, '_callback__'+_name, None)
        _context = getattr(self, '_context__'+_name, None)
        _redraw = getattr(self, '_redraw__'+_name, None)
        if not (_callback or _context or _redraw):
            return

        lprint('CONNECTING', _name, verbose=verbose)

        # Connect callback
        if _callback:

            # Wrap callback
            if isinstance(widget, QtWidgets.QPushButton):
                if track_usage_:
                    from psyhive.tools import track_usage
                    _callback = track_usage(_callback)
                if catch_error_:
                    from psyhive.tools import get_error_catcher
                    _catcher = get_error_catcher(exit_on_error=False)
                    _callback = _catcher(_callback)
                if disable_btns_on_exec:
                    _callback = _disable_while_executing(
                        func=_callback, btn=widget)

            _callback = wrap_fn(_callback)  # To lose args from hook
            lprint(' - CONNECTING', widget, verbose=verbose)

            # Find signals to connect to
            for _hook_name in [
                    'clicked',
                    'currentTextChanged',
                    'textChanged',
            ]:
                _hook = getattr(widget, _hook_name, None)
                if _hook:
                    _hook.connect(_callback)

        # Connect context
        if _context:
            widget.customContextMenuRequested.connect(
                _build_context_fn(_context, widget=widget))
            widget.setContextMenuPolicy(Qt.CustomContextMenu)

        # Connect redraw callback
        if _redraw:
            lprint(' - CONNECTING REDRAW', widget, verbose=verbose)
            _mthd = _build_redraw_method(_redraw)
            widget.redraw = types.MethodType(_mthd, widget)

    def set_icon(self, icon):
        """Set icon for this interface.

        Args:
            icon (str|QPixmap): icon to apply
        """
        from psyhive import qt
        _pix = qt.get_pixmap(icon)
        _icon = qt.get_icon(_pix)
        self.setWindowIcon(_pix)

    def set_redraw_sorting(self, sort):

        self._redraw_sorting = sort

    def delete(self):
        """Delete this interface."""
        self.closeEvent(event=None)
        self.deleteLater()

    def read_settings(self, verbose=1):
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
            self.move(_pos)
        _size = self.settings.value('window/size')
        if _size:
            lprint(' - APPLYING SIZE', _size, verbose=verbose)
            self.resize(_size)

        # Apply widget settings
        for _widget in self.findChildren(QtWidgets.QWidget):
            _name = _widget.objectName()
            _val = self.settings.value(_name)
            if _val is None:
                continue
            lprint(' - APPLY', _name, _val, verbose=verbose)
            self._apply_setting(widget=_widget, value=_val)

    def _apply_setting(self, widget, value, verbose=0):
        """Apply a value from settings to a widget.

        Args:
            widget (QWidget): widget to apply setting to
            value (any): value to apply
            verbose (int): print process data
        """
        if isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(value)

        elif isinstance(widget, (
                QtWidgets.QRadioButton,
                QtWidgets.QCheckBox,
                QtWidgets.QPushButton)):
            if isinstance(value, six.string_types):
                value = {'true': True, 'false': False}[value]
            if isinstance(value, bool):
                widget.setChecked(value)
            else:
                print ' - FAILED TO APPLY:', widget, value, type(value)

        elif isinstance(widget, QtWidgets.QListWidget):
            for _row in range(widget.count()):
                _item = widget.item(_row)
                _item.setSelected(_item.text() in value)

        elif isinstance(widget, QtWidgets.QTabWidget):
            try:
                widget.setCurrentIndex(value)
            except TypeError:
                print ' - FAILED TO APPLY TAB', value

        elif isinstance(widget, QtWidgets.QSplitter):
            value = [int(_item) for _item in value]
            lprint('SET SPLITTER SIZE', value, verbose=verbose)
            widget.setSizes(value)

        elif isinstance(widget, QtWidgets.QLabel):
            pass

        else:
            print 'WIDGET', widget.objectName(), widget
            raise ValueError(
                'Error reading settings '+self.settings.fileName())

    def write_settings(self, verbose=1):
        """Write settings to disk.

        Args:
            verbose (int): print process data
        """
        if not self.settings:
            return
        dprint('WRITING SETTINGS', self.settings.fileName(), verbose=verbose)

        for _widget in self.findChildren(QtWidgets.QWidget):
            if isinstance(_widget, QtWidgets.QLineEdit):
                _val = _widget.text()
            elif isinstance(_widget, (
                    QtWidgets.QRadioButton,
                    QtWidgets.QCheckBox)):
                _val = _widget.isChecked()
            elif (
                    isinstance(_widget, QtWidgets.QPushButton) and
                    _widget.isCheckable()):
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

    def redraw_ui(self, verbose=1):
        """Redraw widgets that need updating."""
        lprint("REDRAW UI", self, verbose=verbose)
        _widgets = self.findChildren(QtWidgets.QWidget)
        if self._redraw_sorting:
            _widgets.sort(key=_self._redraw_sorting)
        for _widget in _widgets:
            _redraw = getattr(_widget, 'redraw', None)
            if _redraw:
                lprint(" - REDRAW", _widget, verbose=verbose)
                _redraw()

    def closeEvent(self, event=None):
        """Trigger by closing interface.

        Args:
            event (QEvent): triggered event
        """
        super(HUiDialog2, self).closeEvent(event)
        print 'CLOSE', self
        self.write_settings()


def get_widget_sort(first=(), last=()):

    def _widget_sort(widget):

        if widget in first:
            _prefix = '0{:010d}'.format(
                int(100000.0*first.index(widget)/len(first)))
        elif widget in last:
            _prefix = '2{:010d}'.format(
                int(100000.0*last.index(widget)/len(last)))
        else:
            _prefix = '1{:010d}'.format(0)

        return _prefix + widget.objectName()

    return _widget_sort 

