"""Tools for reading user input."""

from psyhive.qt.wrapper import QtWidgets
from psyhive.qt.dialog import notify_warning, DialogCancelled


def read_input(
        msg="Enter input:", title="Input dialog", default=None,
        type_=str, width=300, required=False, parent=None):
    """Show an input dialog requesting the user enter data.

    Args:
        msg (str): dialog message
        title (str): dialog title
        default (any): default value for dialog
        type_ (type): type of data to receive
        width (int): dialog width
        required (bool): whether data is required
        parent (QDialog): parent dialog

    Returns:
        (any): entered data of requested type
    """
    _locals = locals()
    _args = [parent] if parent else []

    if type_ is str:
        _default = default or ''
        _dialog = QtWidgets.QInputDialog(*_args)
        _dialog.setInputMode(QtWidgets.QInputDialog.TextInput)
        _dialog.setWindowTitle(title)
        _dialog.setLabelText(msg)
        _dialog.setTextValue(_default)
        _dialog.resize(width, 100)
        _responded = _dialog.exec_()
        _result = str(_dialog.textValue())
    elif type_ is int:
        _default = default or 1
        _result, _responded = QtWidgets.QInputDialog.getInt(
            None, title, msg, _default)
    else:
        raise ValueError('Unhandled type: {}'.format(type_.__name__))

    if _responded in [0, False]:
        raise DialogCancelled

    if required and not _result:
        notify_warning(
            'This dialog requires information to be entered.\n\nPlease enter '
            'some text or press cancel to exit.')
        _result = read_input(**_locals)
        return _result

    return _result
