"""Tools for managing simple dialogs."""

import six

from psyhive import icons
from psyhive.utils import lprint

from psyhive.qt.wrapper.mgr import QtWidgets, QtCore, QtGui
from psyhive.qt.misc import get_application, get_p


class DialogCancelled(RuntimeError):
    """Raised when a dialog is cancelled."""


class _HMessageBox(QtWidgets.QMessageBox):
    """Simple message box interface."""

    def __init__(
            self, text, title, buttons, icon=None, icon_size=None,
            parent=None):
        """Constructor.

        Args:
            text (str): message to display
            title (str): title for the interface
            buttons (str list): buttons to show
            icon (str): path to icon to displau
            icon_size (int): icon size in pixels
            parent (QDialog): parent dialog
        """
        _args = [parent] if parent else []
        super(_HMessageBox, self).__init__(*_args)
        self.setWindowTitle(title)
        self.setText(text)

        self.buttons, self.shortcuts = self._add_buttons(buttons)
        self._add_icon(icon=icon, icon_size=icon_size)

        self._force_result = None

    def _add_buttons(self, buttons):
        """Add the buttons to the interface.

        Args:
            buttons (str list): buttons to show
        """

        # Get list of buttons to create
        _buttons = list(buttons)

        # Create buttons
        _btn_map = {}
        for _button in _buttons:
            _btn_map[_button] = self.addButton(
                _button, QtWidgets.QMessageBox.AcceptRole)

        # Make sure we have cancel behaviour
        if "Cancel" not in _btn_map:
            _btn_map["Cancel"] = self.addButton(
                "Cancel", QtWidgets.QMessageBox.AcceptRole)
            _btn_map["Cancel"].hide()
            _buttons += ["Cancel"]
        self.setEscapeButton(_btn_map["Cancel"])
        self.setDefaultButton(_btn_map["Cancel"])

        # Read shortcuts
        _shortcuts = {}
        for _button in _buttons:
            if _button == 'Cancel':
                continue
            if not _button[0] in _shortcuts:
                _shortcuts[_button[0]] = _button
            else:
                del _shortcuts[_button[0]]

        return _buttons, _shortcuts

    def _add_icon(self, icon, icon_size):
        """Add the icon to the interface.

        Args:
            icon (str): path to icon
            icon_size (int): icon size in pixels
        """
        if not icon:
            return

        if isinstance(icon, six.string_types):
            _pixmap = QtGui.QPixmap(icon)
        elif isinstance(icon, QtGui.QPixmap):
            _pixmap = icon
        else:
            raise ValueError(_pixmap)
        if icon_size is None:
            if _pixmap.width() == 144 and _pixmap.height() == 144:
                icon_size = 72
        if icon_size:
            _pixmap = _pixmap.scaled(icon_size, icon_size)
        self.setIconPixmap(_pixmap)

    def get_result(self):
        """Read the result of the dialog."""
        _exec_result = self.exec_()

        # Interpret result
        if self._force_result:
            _result = self._force_result
        else:
            _result = self._force_result or self.buttons[_exec_result]
        if _result == "Cancel":
            raise DialogCancelled

        return _result

    def keyPressEvent(self, event):
        """Executed on key press event.

        Args:
            event (QKeyEvent): triggered event
        """
        _result = super(_HMessageBox, self).keyPressEvent(event)

        _key = chr(event.key()) if event.key() < 256 else None
        _alt = event.modifiers() == QtCore.Qt.AltModifier

        if _key and _alt and _key in self.shortcuts:
            _result = self.shortcuts[_key]
            self._force_result = _result
            self.close()

        return _result


def ok_cancel(
        msg, title='Confirm', icon=None, pos=None, parent=None,
        verbose=1):
    """Show a simple dialog with Ok and Cancel buttons.

    If ok is selected the code continues, otherwise an error is raised.

    Args:
        msg (str): message for dialog
        title (str): title for dialog
        icon (str): path to icon to display
        pos (QPoint): dialog position
        parent (QDialog): parent dialog
        verbose (int): print process data

    Raises:
        (DialogCancelled): if cancel is pressed
    """
    _icon = icon or icons.EMOJI.find('Thinking')
    raise_dialog(
        msg=msg, title=title, icon=_icon, pos=pos, verbose=verbose,
        parent=parent)


def notify(
        msg, title='Notification', icon=None, icon_size=None, pos=None,
        parent=None):
    """Raise a notification dialog.

    Args:
        msg (str): notification message
        title (str): dialog title
        icon (str): path to dialog icon
        icon_size (int): icon size in pixels
        pos (QPoint): dialog position
        parent (QDialog): parent dialog
    """
    raise_dialog(
        msg=msg, title=title, buttons=['Ok'], icon_size=icon_size,
        icon=icon or icons.EMOJI.find('Slightly Smiling Face'),
        pos=pos, parent=parent)


def notify_warning(msg, title='Warning', icon=None):
    """Raise a warning notification dialog.

    Args:
        msg (str): notification message
        title (str): dialog title
        icon (str): path to dialog icon
    """
    notify(
        msg=msg, title=title,
        icon=icon or icons.EMOJI.find('Cold Face'))


def raise_dialog(
        msg="No message", title="Dialog", buttons=("Ok", "Cancel"),
        icon=None, icon_size=None, pos=None, parent=None, verbose=1):
    """Raise a simple message box dialog.

    Args:
        msg (str): message to show in dialog
        title (str): dialog window title
        buttons (str list): list of buttons to display
        icon (str): path to icon to display
        icon_size (int): icon size in pixels
        pos (QPoint): dialog position
        parent (QDialog): parent dialog
        verbose (int): print process data
    """
    get_application()
    _box = _HMessageBox(
        title=title, text=msg, buttons=buttons, icon=icon, icon_size=icon_size,
        parent=parent)
    if '\n' in msg:
        lprint('[dialog]', verbose=verbose)
        lprint(msg, verbose=verbose)
    else:
        lprint('[dialog] '+msg, verbose=verbose)
    if pos:
        _box.show()  # To calculate size
        _box.move(pos-get_p(_box.size())/2)
    return _box.get_result()


def yes_no_cancel(msg, title='Confirm', icon=None, pos=None):
    """Show a simple dialog with Yes/No/Cancel buttons.

    If ok is selected the code continues, otherwise an error is raised.

    Args:
        msg (str): message for dialog
        title (str): title for dialog
        icon (str): path to icon to display
        pos (QPoint): dialog position

    Returns:
        (str): dialog result

    Raises:
        (DialogCancelled): if cancel is pressed
    """
    _icon = icon or icons.EMOJI.find('Thinking')
    return raise_dialog(
        msg=msg, title=title, icon=_icon, pos=pos,
        buttons=['Yes', 'No', 'Cancel'])
