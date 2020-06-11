"""General utiliteis for managing paths."""

import functools
import os


def restore_cwd(func):
    """Decorator to restore cwd after executing a function.

    Args:
        func (fn): function to decorate
    """

    @functools.wraps(func)
    def _restore_cwd_fn(*args, **kwargs):
        _cwd = os.getcwd()
        _result = func(*args, **kwargs)
        os.chdir(_cwd)
        return _result

    return _restore_cwd_fn


class FileError(RuntimeError):
    """Raises when a file causes an issue."""

    def __init__(self, message, file_, line_n=None):
        """Constructor.

        Args:
            message (str): error message
            file_ (str): path to file
            line_n (int): line of file causing issue
        """
        super(FileError, self).__init__(message)
        self.file_ = file_
        self.line_n = line_n
