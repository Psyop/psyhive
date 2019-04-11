"""Tools for managing classes in a python file."""

import ast

from psyhive.utils.misc import to_nice

from psyhive.utils.py_file.docs import MissingDocs
from psyhive.utils.py_file.base import PyBase


class PyClass(PyBase):
    """Represents a python class."""

    def check_docs(self, recursive=False, verbose=0):
        """Check this file's docstrings.

        Args:
            recursive (bool): recursively check child objects docs
            verbose (int): print process data
        """
        _docs = ast.get_docstring(self._ast)
        if not _docs:
            raise MissingDocs('No class docs')
        if not _docs.endswith('.'):
            raise MissingDocs('No trailing period')

    def get_docs_suggestion(self, verbose=0):
        """Get suggestion for this def's docstring.

        Args:
            verbose (int): print process data
        """
        _header = to_nice(self.name)
        _indent = ' '*4*(self._ast.col_offset+1)
        return '{}"""{}"""'.format(_indent, _header)
