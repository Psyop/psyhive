"""Tools for catching errors."""

import functools
import os
import sys
import traceback

from psyhive import qt
from psyhive.utils import (
    abs_path, check_heart, File, FileError, lprint, dprint, dev_mode)

_UI_FILE = abs_path('err_dialog.ui', root=os.path.dirname(__file__))


class _ErrDialog(qt.HUiDialog):
    """Dialog for managing code errors."""

    def __init__(self, traceback_, message):
        """Constructor.

        Args:
            traceback_ (_Traceback): traceback object
            message (str): error message
        """
        self.traceback = traceback_
        self.message = message
        super(_ErrDialog, self).__init__(ui_file=_UI_FILE)
        self.ui.setWindowTitle('Error')

    def _callback__er_view_code(self):

        _line = self.ui.er_traceback.currentItem().data(qt.QtCore.Qt.UserRole)
        _line.edit()

    def _redraw__er_message(self, widget):
        _text = 'There has been an error'
        if not self.message:
            _text += '.'
        else:
            _text += ':\n\n{}'.format(self.message)
        widget.setText(_text)

    def _redraw__er_traceback(self, widget):
        widget.clear()
        for _line in reversed(self.traceback.lines):
            _item = qt.QtWidgets.QListWidgetItem(_line.text)
            _item.setData(qt.QtCore.Qt.UserRole, _line)
            widget.addItem(_item)
        widget.setCurrentRow(0)


class _TraceStep(object):
    """Represents a step in a traceback.

    This is generated from a pair of lines in a traceback string.
    """

    def __init__(self, lines):
        """Constructor.

        Args:
            lines (list): traceback lines
        """
        self.text = lines[0].strip()+'\n  '+lines[1].strip()
        self.file_ = abs_path(lines[0].split('"')[1])
        self.line_n = int(lines[0].split(',')[1].strip(' line'))

    def edit(self):
        """Edit the code of this traceback link."""
        File(self.file_).edit(line_n=self.line_n)


class _Traceback(object):
    """Represents a traceback."""

    def __init__(self, traceback_=None):
        """Constructor.

        Args:
            traceback_ (str): override traceback string
                (otherwise read from traceback module)
        """
        self.body = (traceback_ or traceback.format_exc()).strip()
        self.lines = []
        _lines = self.body.split('\n')
        assert _lines.pop(0) == 'Traceback (most recent call last):'
        while len(_lines) > 2:
            check_heart()
            try:
                _trace_line = _TraceStep([_lines.pop(0), _lines.pop(0)])
            except IndexError:
                print '[traceback]'
                print self.body
                raise RuntimeError('Failed to parse traceback')
            self.lines.append(_trace_line)


def _handle_exception(exc, verbose=0):
    """Handle the given exception.

    Args:
        exc (Exception): exception that was raised
        verbose (int): print process data
    """

    # In case of FileError, jump to file
    if (
            not os.environ.get('EXC_DISABLE_FILE_ERROR') and
            isinstance(exc, FileError)):
        print '[FileError]'
        print ' - MESSAGE:', exc.message
        print ' - FILE:', exc.file_
        File(exc.file_).edit(line_n=exc.line_n)
        return

    # Ignore DialogCancelled
    if isinstance(exc, qt.DialogCancelled):
        print '[DialogCancelled]'
        return

    if not dev_mode():
        _pass_exception_to_sentry(exc)

    # Raise error dialog
    lprint('HANDLING EXCEPTION', exc, verbose=verbose)
    lprint('MSG', exc.message, verbose=verbose)
    lprint('TYPE', type(exc), verbose=verbose)
    _traceback = _Traceback()
    _app = qt.get_application()
    _dialog = _ErrDialog(traceback_=_traceback, message=exc.message)


def catch_error(func):
    """Decorator which raises an error handler dialog if a function errors.

    Args:
        func (fn): function to decorate
    """

    @functools.wraps(func)
    def _catch_error_fn(*args, **kwargs):
        if os.environ.get('EXC_DISABLE_ERR_CATCHER'):
            return func(*args, **kwargs)
        try:
            _result = func(*args, **kwargs)
        except Exception as _exc:
            _handle_exception(_exc)
            sys.exit()

        return _result

    return _catch_error_fn


def launch_err_catcher(traceback_, message):
    """Launch error catcher dialog with the given message/traceback.

    Args:
        traceback_ (str): traceback
        message (str): error message
    """
    _traceback = _Traceback(traceback_)
    _dialog = _ErrDialog(traceback_=_traceback, message=message)
    _dialog.ui.exec_()


def _pass_exception_to_sentry(exc):
    """Send exception data to sentry.

    Args:
        exc (Exception): exception that was raised
    """
    print 'PASSING EXCEPTION TO SENTRY', exc

    import psyop.utils
    _logger = psyop.utils.get_logger('psyhive')
    _logger.exception(str(exc))


def toggle_err_catcher():
    """Toggle error catcher decorator."""
    if os.environ.get('EXC_DISABLE_ERR_CATCHER'):
        del os.environ['EXC_DISABLE_ERR_CATCHER']
        dprint("Enabled error catcher")
    else:
        os.environ['EXC_DISABLE_ERR_CATCHER'] = '1'
        dprint("Disabled error catcher")


def toggle_file_errors():
    """Toggle error catcher decorator."""
    if os.environ.get('EXC_DISABLE_FILE_ERROR'):
        del os.environ['EXC_DISABLE_FILE_ERROR']
        dprint("Enabled file errors")
    else:
        os.environ['EXC_DISABLE_FILE_ERROR'] = '1'
        dprint("Disabled file errors")
