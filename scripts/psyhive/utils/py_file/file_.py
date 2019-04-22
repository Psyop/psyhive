"""Tools for managing python files."""

import ast
import sys

from psyhive.utils.cache import store_result_on_obj
from psyhive.utils.path import File, abs_path, rel_path, FileError
from psyhive.utils.misc import dprint, lprint

from psyhive.utils.py_file.docs import MissingDocs
from psyhive.utils.py_file.base import PyBase


class PyFile(File, PyBase):
    """Represents a python file."""

    def __init__(self, path, body=None):
        """Constructor.

        Args:
            path (str): path to python file
            body (str): override body of python file (advanced)
        """
        self.body = body
        super(PyFile, self).__init__(path)

        if not self.extn == 'py':
            raise ValueError(path)

        PyBase.__init__(self, ast_=None, py_file=self, name=self.basename)

    def check_docs(self, recursive=True, verbose=0):
        """Check this file's docstrings.

        Args:
            recursive (bool): recursively check child objects docs
            verbose (int): print process data
        """
        _docs = ast.get_docstring(self._get_ast())
        if self._get_ast().body and not _docs:
            raise MissingDocs('No module docs')

        if recursive:
            for _obj in self.find_children():
                _obj.check_docs()

    def fix_docs(self, recursive=True):
        """Fix this py file's docstrings.

        Args:
            recursive (bool): also fix children's children recursively
        """
        try:
            self.check_docs(recursive=False)
        except MissingDocs as _exc:
            raise FileError(_exc.message, file_=self.path)

        for _obj in self.find_children():
            _obj.fix_docs()

        dprint('FIX DOCS COMPLETE')

    @store_result_on_obj
    def _get_ast(self, force=False):
        """Get this py file's ast object.

        Args:
            force (bool): force reread ast object from disk

        Returns:
            (ast.Module): abstract syntax tree
        """
        _body = self.body or self.read()
        try:
            return ast.parse(_body)
        except IndentationError as _exc:
            print 'INDENTATION ERROR', self.path
            raise _exc

    def get_module(self, catch=False, verbose=0):
        """Get the python module associated with this py file.

        Args:
            catch (bool): no error if module fails to import
            verbose (int): print process data

        Returns:
            (mod): imported module
            (None): if module failed to import and catch used
        """
        lprint("GET MODULE", self.path, verbose=verbose)

        _sys_paths = sorted(set([
            abs_path(_path) for _path in sys.path
            if self.path.startswith(abs_path(_path))]))
        _sys_paths.sort(key=len)
        _sys_path = _sys_paths[-1]
        _rel_path = rel_path(self.path, _sys_path)
        _mod_name = _rel_path.replace('.py', '').replace('/', '.')

        # Try to import the module
        if _mod_name not in sys.modules:
            try:
                __import__(_mod_name, fromlist=_mod_name.split('.'))
            except ImportError as _exc:
                if catch:
                    return None
                raise _exc

        return sys.modules[_mod_name]


def text_to_py_file(text):
    """Create a dummy py file object using the given text.

    This is mainly for testing.

    Args:
        text (str): py file body
    """
    return PyFile('C:/dummy/path.py', body=text)
