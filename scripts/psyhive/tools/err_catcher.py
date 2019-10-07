"""Tools for catching errors."""

import functools
import os
import sys
import traceback
import urllib
import webbrowser

from psyhive import qt, icons, host, pipe
from psyhive.utils import (
    abs_path, check_heart, File, FileError, lprint, dprint, dev_mode,
    copy_text)

_UI_FILE = abs_path('err_dialog.ui', root=os.path.dirname(__file__))


class HandledError(Exception):
    """Base class for any exception to be ignored by the catcher.

    Rather than displaying the error dialog, this error with just
    display a notification dialog.
    """

    def __init__(self, message, icon=None, title=None):
        """Constructor.

        Args:
            message (str): dialog message
            icon (str): path to dialog icon
            title (str): title for dialog
        """
        super(HandledError, self).__init__(message)
        self.icon = icon or icons.EMOJI.find('Cold face')
        self.title = title or 'Error'


class _ErrDialog(qt.HUiDialog):
    """Dialog for managing code errors."""

    def __init__(self, traceback_, message, type_=None):
        """Constructor.

        Args:
            traceback_ (Traceback): traceback object
            message (str): error message
            type_ (str): name of error type
        """
        self.traceback = traceback_
        self.message = message
        self.type_ = type_

        super(_ErrDialog, self).__init__(
            ui_file=_UI_FILE, catch_error_=False)
        self.setWindowTitle('Error')

    def _redraw__er_message(self, widget):
        _text = 'There has been an error ({})'.format(self.type_)
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

    def _callback__er_copy_text(self):
        copy_text('```\n{}\n```'.format(self.traceback.clean_text))

    def _callback__er_make_ticket(self):

        _desc = '\n'.join([
            'HOST: {}'.format(host.NAME),
            'PROJECT: {}'.format(pipe.cur_project().name),
            'SCENE: {}'.format(host.cur_scene()),
            '',
            'TRACEBACK:',
            '```',
            self.traceback.clean_text,
            '```'])
        _make_ticket(
            summary='[PSYHIVE] Error: {}'.format(self.message),
            description=_desc)

    def _callback__er_view_code(self):
        _line = self.ui.er_traceback.currentItem().data(qt.QtCore.Qt.UserRole)
        _line.edit()


class _TraceStep(object):
    """Represents a step in a traceback.

    This is generated from a pair of lines in a traceback string.
    """

    def __init__(self, lines):
        """Constructor.

        Args:
            lines (list): traceback lines
        """
        self.text = '\n  '.join([_line.strip() for _line in lines])
        self.file_ = abs_path(lines[0].split('"')[1])
        self.line_n = int(lines[0].split(',')[1].strip(' line'))

    def edit(self):
        """Edit the code of this traceback link."""
        File(self.file_).edit(line_n=self.line_n)


class Traceback(object):
    """Represents a traceback."""

    def __init__(self, traceback_=None):
        """Constructor.

        Args:
            traceback_ (str): override traceback string
                (otherwise read from traceback module)
        """
        self.body = (traceback_ or traceback.format_exc()).strip()
        _lines = self.body.split('\n')
        assert _lines.pop(0) == 'Traceback (most recent call last):'

        _file_lines = []
        while _lines and _lines[0] and _lines[0].startswith(' '):
            check_heart()
            _file_lines.append(_lines.pop(0))
        _file_text = '\n'.join(_file_lines)
        _splitter = '  File "'
        try:
            self.lines = [
                _TraceStep((_splitter+_item).strip().split('\n'))
                for _item in _file_text.split(_splitter)[1:]]
        except IndexError:
            print '############## Traceback ##############'
            print self.body
            print '#######################################'
            raise RuntimeError("Failed to parse traceback")

        self.clean_text = '# '+self.body.replace('\n', '\n# ')
        for _token in self.clean_text.split('"'):
            if os.path.exists(_token):
                _path = abs_path(_token)
                self.clean_text = self.clean_text.replace(_token, _path)

    def pprint(self):
        """Print this traceback in maya format."""
        print self.clean_text


def _handle_exception(exc, verbose=0):
    """Handle the given exception.

    Args:
        exc (Exception): exception that was raised
        verbose (int): print process data
    """

    # Handle special exceptions
    if (  # In case of FileError, jump to file
            not os.environ.get('EXC_DISABLE_FILE_ERROR') and
            isinstance(exc, FileError)):
        print '[FileError]'
        print ' - MESSAGE:', exc.message
        print ' - FILE:', exc.file_
        File(exc.file_).edit(line_n=exc.line_n)
        return
    elif isinstance(exc, qt.DialogCancelled):
        print '[DialogCancelled]'
        return
    elif isinstance(exc, HandledError):
        qt.notify_warning(msg=exc.message, icon=exc.icon, title=exc.title)
        return

    if not dev_mode():
        _pass_exception_to_sentry(exc)

    # Raise error dialog
    lprint('HANDLING EXCEPTION', exc, verbose=verbose)
    lprint('MSG', exc.message, verbose=verbose)
    lprint('TYPE', type(exc), verbose=verbose)
    _traceback = Traceback()
    _traceback.pprint()
    _app = qt.get_application()
    _dialog = _ErrDialog(
        traceback_=_traceback, message=exc.message,
        type_=type(exc).__name__)


def catch_error(func):
    """Decorator which raises an error handler dialog if a function errors.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """
    return get_error_catcher()(func)


def launch_err_catcher(traceback_, message):
    """Launch error catcher dialog with the given message/traceback.

    Args:
        traceback_ (str): traceback
        message (str): error message
    """
    _traceback = Traceback(traceback_)
    _dialog = _ErrDialog(traceback_=_traceback, message=message)


def get_error_catcher(exit_on_error=True, verbose=1):
    """Build an error catcher decorator.

    Args:
        exit_on_error (bool): raise sys.exit on error (this should be
            avoided for an error raised in a maya qt thread as it can
            cause a seg fault)
        verbose (int): print process data
    """

    def _error_catcher(func):

        @functools.wraps(func)
        def _catch_error_fn(*args, **kwargs):

            # Handle catcher disabled
            if os.environ.get('EXC_DISABLE_ERR_CATCHER'):
                lprint(' - ERROR CATCHER DISABLED', verbose=verbose)
                return func(*args, **kwargs)

            # Catch function fails
            lprint(
                ' - EXECUTING FUNCTION', func.__name__,
                verbose=verbose > 1)
            try:
                _result = func(*args, **kwargs)
            except Exception as _exc:
                lprint('EXCEPTION', func, args, kwargs, verbose=verbose)
                _handle_exception(_exc)
                if exit_on_error:
                    sys.exit()
                return None
            lprint(
                ' - EXECUTED FUNCTION', func.__name__,
                verbose=verbose > 1)

            return _result

        return _catch_error_fn

    return _error_catcher


def _make_ticket(summary, description):
    """Open a browser at the create YouTrack ticket page.

    The fields should be filled out with summary/description/assignee.

    Args:
        summary (str): ticket summary/title
        description (str): ticket description
    """
    _url = ('https://ticket.ny.psyop.tv/newIssue?'
            'summary={}&description={}'
            '&c=Type%20Performance%20Problem'
            '&c=Assignee%20hvanderbeek')
    webbrowser.open(_url.format(
        urllib.quote_plus(summary), urllib.quote_plus(description)))


def _pass_exception_to_sentry(exc):
    """Send exception data to sentry.

    Args:
        exc (Exception): exception that was raised
    """
    if os.environ.get('EXC_DISABLE_SENTRY'):
        return
    print 'PASSING EXCEPTION TO SENTRY', exc
    try:
        import psyop.utils
    except ImportError:
        print 'FAILED TO CREATE PSYOP LOGGER'
        return
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
