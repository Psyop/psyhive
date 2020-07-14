"""Tools for managing python files."""

import ast
import sys
import traceback

from psyhive.utils.cache import store_result_on_obj
from psyhive.utils.path import File, abs_path, rel_path, FileError
from psyhive.utils.misc import dprint, lprint

from psyhive.utils.py_file.docs import MissingDocs
from psyhive.utils.py_file.base import PyBase


class PyFile(File, PyBase):
    """Represents a python file."""

    def __init__(self, path, body=None, check_extn=True):
        """Constructor.

        Args:
            path (str): path to python file
            body (str): override body of python file (advanced)
            check_extn (bool): check file has py extn
        """
        self.body = body
        super(PyFile, self).__init__(path)
        if check_extn and not self.extn == 'py':
            raise ValueError(path)
        PyBase.__init__(self, ast_=None, py_file=self, name=self.basename)

    @property
    def docs(self):
        """Get docstrings for this module.

        Since it requires reading the ast, it's stored as a property.

        Returns:
            (str): module docstrings
        """
        try:
            return ast.get_docstring(self.get_ast())
        except SyntaxError:
            return None

    def check_docs(self, recursive=True, verbose=0):
        """Check this file's docstrings.

        Args:
            recursive (bool): recursively check child objects docs
            verbose (int): print process data
        """
        _docs = ast.get_docstring(self.get_ast())
        if self.get_ast().body and not _docs:
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
    def get_ast(self, force=False):
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
        except SyntaxError as _exc:
            _msg = 'Syntax error at line {:d} in file {}'.format(
                _exc.lineno, self.path)
            raise FileError(_msg, file_=self.path, line_n=_exc.lineno)

    def get_module(self, catch=False, reload_=False, verbose=0):
        """Get the python module associated with this py file.

        Args:
            catch (bool): no error if module fails to import
            reload_ (bool): reload module
            verbose (int): print process data

        Returns:
            (mod): imported module
            (None): if module failed to import and catch used
        """
        _path = abs_path(self.path)
        lprint("GET MODULE", _path, verbose=verbose)

        _sys_paths = sorted(set([
            abs_path(_spath) for _spath in sys.path
            if _path.startswith(abs_path(_spath))]))
        _sys_paths.sort(key=len)
        if not _sys_paths:
            if catch:
                return None
            raise RuntimeError('Failed to find sys path '+_path)
        _sys_path = _sys_paths[-1]
        lprint('ROOT', _sys_path, verbose=verbose)
        _rel_path = rel_path(path=_path, root=_sys_path)
        lprint('REL PATH', _rel_path, verbose=verbose)
        _mod_name = _rel_path.replace('.py', '').replace('/', '.')
        lprint('MOD NAME', _mod_name, verbose=verbose)

        # Try to import the module
        if _mod_name not in sys.modules:
            try:
                __import__(_mod_name, fromlist=_mod_name.split('.'))
            except Exception as _exc:
                if catch:
                    return None
                print 'FAILED TO IMPORT MODULE', self.path
                _trace = traceback.format_exc().strip()
                print '# '+'\n# '.join(_trace.split('\n'))
                sys.exit()

        _mod = sys.modules[_mod_name]
        if reload_:
            reload(_mod)

        return _mod


def text_to_py_file(text):
    """Create a dummy py file object using the given text.

    This is mainly for testing.

    Args:
        text (str): py file body
    """
    return PyFile('C:/dummy/path.py', body=text)
