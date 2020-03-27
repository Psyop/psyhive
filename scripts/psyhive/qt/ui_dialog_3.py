"""Tools for managing HUiDialog3.

Previous iterations have garbage collections issues. This aims to rebuild
the same functionality, but avoiding wrapping widgets which seemed to
create issues.
"""

import operator
import sys

import six

from psyhive.qt import QtCore, QtWidgets, Qt
from psyhive.utils import abs_path, lprint, File, touch, dprint, dev_mode

from psyhive.qt.ui_dialog import _SETTINGS_DIR

PYGUI_COL = 'Yellow'


def _get_widget_label(widget):
    """Get label for a widget - eg. <QPushButton:MyButton>.

    Args:
        widget (QWidget): widget to read

    Returns:
        (str): button label
    """
    _name = widget.objectName()
    return '<{}:{}>'.format(type(widget).__name__, _name)


class HUiDialog3(QtWidgets.QDialog):
    """Dialog based on a ui file."""

    def __init__(self, ui_file, catch_errors_=True, save_settings=True,
                 parent=None):
        """Constructor.

        Args:
            ui_file (str): path to ui file
            catch_errors_ (bool): apply error catcher to callbacks
            save_settings (bool): load/save settings on open/close
            parent (QWidget): override parent widget
        """
        from psyhive import host
        self.ui_file = ui_file
        self._register_in_dialog_stack()

        super(HUiDialog3, self).__init__(
            parent=parent or host.get_main_window_ptr())

        self._load_ui()
        self._connect_elements(catch_errors_=catch_errors_)

        self.init_ui()
        self.disable_save_settings = not save_settings
        self.load_settings()

        self.show()

    def init_ui(self):
        """This is used in subclass to initiate elements.

        This is executed before load settings.
        """

    def _register_in_dialog_stack(self):
        """Register this dialog in the dialog stack.

        Any existing dialog with this ui file is closed.
        """

        # Clean existing uis
        if self.ui_file in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[self.ui_file].delete()

        sys.QT_DIALOG_STACK[self.ui_file] = self

    def _load_ui(self):
        """Load ui file."""
        from psyhive import qt
        self.ui = qt.get_ui_loader().load(self.ui_file)
        self.resize(self.ui.size())
        if not self.ui.layout():
            raise RuntimeError('HUiDialog3 requires root level layout in ui')
        self.setLayout(self.ui.layout())
        self.setWindowTitle(self.ui.windowTitle())

    def _connect_elements(self, catch_errors_=False, verbose=0):
        """Connect qt elements to callback/context methods.

        Args:
            catch_errors_ (bool): apply error catcher to callbacks
            verbose (int): print process data
        """
        from psyhive.tools import err_catcher
        _err_catcher = err_catcher.get_error_catcher(remove_args=True)

        # Get list of widgets
        _widgets = self.findChildren(QtWidgets.QWidget)
        _widgets = [_widget for _widget in _widgets
                    if _is_pascal(_widget.objectName())]
        _widgets.sort(key=operator.methodcaller('objectName'))

        for _widget in _widgets:

            _name = _widget.objectName()
            if not _name or _name.startswith('qt_'):
                continue
            lprint(_get_widget_label(_widget), verbose=verbose)

            # Connect callback
            _callback = getattr(self, '_callback__'+_name, None)
            if _callback:
                if catch_errors_:
                    _callback = _err_catcher(_callback)
                _signal = None
                if isinstance(_widget, QtWidgets.QListWidget):
                    _signal = _widget.itemSelectionChanged
                elif isinstance(_widget, QtWidgets.QComboBox):
                    _signal = _widget.currentIndexChanged
                elif isinstance(_widget, QtWidgets.QLineEdit):
                    _signal = _widget.textChanged
                elif isinstance(_widget, QtWidgets.QPushButton):
                    _signal = _widget.clicked
                elif isinstance(_widget, QtWidgets.QTabWidget):
                    _signal = _widget.currentChanged
                if _signal:
                    _signal.connect(_callback)
                    lprint(' - CONNECTING CALLBACK', _callback,
                           verbose=verbose)

            # Connect context
            _context = getattr(self, '_context__'+_name, None)
            if _context:
                _widget.customContextMenuRequested.connect(
                    _build_context_fn(_context, widget=_widget))
                _widget.setContextMenuPolicy(Qt.CustomContextMenu)
                lprint(' - CONNECTING CONTEXT', _context, verbose=verbose)

        if dev_mode():
            self._catch_unconnected_callbacks()
            self._catch_duplicate_tooltips()

    def _catch_unconnected_callbacks(self):
        """Error if unconnected callbacks are found.

        These are callack/redraw/context methods without a corresponding
        element in the dialog's ui object.
        """
        for _name in dir(self):
            _tokens = _name.split('__')
            if len(_tokens) != 2 or _tokens[0] not in (
                    '_callback', '_redraw', '_context'):
                continue
            _elem_name = _tokens[1]
            _elem = getattr(self.ui, _elem_name, None)
            if not _elem:
                raise RuntimeError('Unconnected method '+_name)

    def _catch_duplicate_tooltips(self):
        """Error if duplicate tooltips are found.

        These are often overlooked when duplicating elements in designer
        and can cause confusion if elements are badly tooltipped.
        """
        _tooltips = {}
        for _widget in self.findChildren(QtWidgets.QWidget):
            _tooltip = _widget.toolTip()
            if not _tooltip:
                continue
            if _tooltip in _tooltips:
                print _get_widget_label(_tooltips[_tooltip])
                print _get_widget_label(_widget)
                print _tooltip
                raise RuntimeError('Duplicate tooltip {}/{} - {}'.format(
                    _tooltips[_tooltip].objectName(),
                    _widget.objectName(), _tooltip))
            _tooltips[_tooltip] = _widget

    @property
    def settings(self):
        """Get settings object.

        Returns:
            (QSettings): settings
        """
        _settings_file = abs_path('{}/{}.ini'.format(
            _SETTINGS_DIR, File(self.ui_file).basename))
        touch(_settings_file)  # Check settings writable
        return QtCore.QSettings(
            _settings_file, QtCore.QSettings.IniFormat)

    def load_settings(self, verbose=0):
        """Read settings from disk.

        Args:
            verbose (int): print process data
        """
        if self.disable_save_settings:
            return
        dprint('LOAD SETTINGS', self.settings.fileName(), verbose=verbose)

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
            self._load_setting(widget=_widget, value=_val)

    def _load_setting(self, widget, value, verbose=0):
        """Apply a value from settings to a widget.

        Args:
            widget (QWidget): widget to apply setting to
            value (any): value to apply
            verbose (int): print process data
        """
        _value = value

        if isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(_value)

        elif isinstance(widget, (
                QtWidgets.QRadioButton,
                QtWidgets.QCheckBox,
                QtWidgets.QPushButton)):
            if isinstance(_value, six.string_types):
                _value = {'true': True, 'false': False}[_value]
            if isinstance(_value, bool):
                widget.setChecked(_value)
            else:
                print ' - FAILED TO APPLY:', widget, _value, type(_value)

        elif isinstance(widget, QtWidgets.QListWidget):
            _load_setting_list_widget(value=_value, widget=widget)

        elif isinstance(widget, QtWidgets.QTabWidget):
            try:
                widget.setCurrentIndex(_value)
            except TypeError:
                print ' - FAILED TO APPLY TAB', _value

        elif isinstance(widget, QtWidgets.QSplitter):
            _value = [int(_item) for _item in _value]
            lprint('SET SPLITTER SIZE', _value, verbose=verbose)
            widget.setSizes(_value)

        elif isinstance(widget, QtWidgets.QLabel):
            pass

        else:
            print 'WIDGET', widget.objectName(), widget
            raise ValueError(
                'Error reading settings '+self.settings.fileName())

    def save_settings(self, verbose=0):
        """Save dialog settings.

        Args:
            verbose (int): print process data
        """
        if self.disable_save_settings:
            return
        dprint('SAVE SETTINGS', self.settings, verbose=verbose)

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

        self.settings.setValue('window/pos', self.pos())
        lprint(' - SAVING POS', self.pos(), verbose=verbose)
        self.settings.setValue('window/size', self.size())
        lprint(' - SAVING SIZE', self.size(), verbose=verbose)

    def set_icon(self, icon):
        """Set icon for this interface.

        Args:
            icon (str|QPixmap): icon to apply
        """
        from psyhive import qt
        _pix = qt.get_pixmap(icon)
        _icon = qt.get_icon(_pix)
        self.setWindowIcon(_pix)
        self.ui.setWindowIcon(_pix)

    def get_c(self):
        """Get interface centre.

        Returns:
            (QPoint): centre
        """
        from psyhive import qt
        return self.pos()+qt.get_p(self.size()/2)

    def delete(self):
        """Delete this interface."""
        self.deleteLater()

    def closeEvent(self, event=None):
        """Executed on close.

        Args:
            event (QEvent): trigged event
        """
        self.save_settings()
        super(HUiDialog3, self).closeEvent(event)


def _build_context_fn(callback, widget):
    """Build function connect widget right-click to the given callback.

    Args:
        callback (fn): context menu callback to connect to
        widget (QWidget): widget to apply callback to
    """

    def _context_fn(pos):
        from psyhive import qt
        _menu = qt.HMenu(widget)
        callback(_menu)
        _menu.exec_(widget.mapToGlobal(pos))

    return _context_fn


def _is_pascal(string):
    """Test if a string is pascal case (eg. ThisIsPascal).

    Args:
        string (str): string to text

    Returns:
        (str): whether string is pascal
    """
    if not string:
        return False
    if not string[0].isupper():
        return False
    for _chr in ' _':
        if _chr in string:
            return False
    return True


def _load_setting_list_widget(widget, value):
    """Load a QListWidget setting.

    If the stored value does not match any items in the list then
    the widget is left unchanged.

    Args:
        widget (QListWidget): widget to apply setting to
        value (str list): stored setting to apply
    """
    _items = [widget.item(_idx) for _idx in range(widget.count())]
    if not [_item for _item in _items if _item.text() in value]:
        return
    for _item in _items:
        _item.setSelected(_item.text() in value)
