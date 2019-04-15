"""Base class for any python component."""

import ast
import operator

from psyhive.utils.filter_ import apply_filter
from psyhive.utils.cache import store_result_on_obj
from psyhive.utils.misc import copy_text, lprint, get_single
from psyhive.utils.path import FileError

from psyhive.utils.py_file.docs import MissingDocs


class PyBase(object):
    """Base class for any component of a python file."""

    def __init__(self, ast_, py_file, name=None):
        """Constructor.

        Args:
            ast_ (ast.Module): ast module for this object
            py_file (PyFile): parent python file for this object
            name (str): override name for this object
        """
        from psyhive.utils.py_file.file_ import PyFile
        assert isinstance(py_file, PyFile)

        self._ast = ast_
        self.py_file = py_file
        self.name = name or ast_.name

    def check_docs(self, recursive=False, verbose=0):
        """Check this def's docstring.

        Args:
            recursive (bool): recursively check child docs
            verbose (int): print process data
        """

    def edit(self):
        """Open this component in a editor."""
        self.py_file.edit(line_n=self._ast.lineno)

    def find_children(self, filter_=None, recursive=False):
        """Find children of this object.

        Args:
            filter_ (str): apply filter to list of children
            recursive (bool): also check children's children recursively
        """
        if not recursive:
            _objs = self._read_children()
        else:
            _objs = []
            for _obj in self._read_children():
                _objs.append(_obj)
                _objs += _obj.find_children(recursive=True)

        if filter_:
            _objs = apply_filter(
                _objs, filter_, key=operator.attrgetter('name'))
        return _objs

    def find_def(self, match=None, recursive=False, catch=False):
        """Find child def.

        Args:
            match (str): def name to search for
            recursive (bool): also check children's children recursively
            catch (bool): no error on fail to find def

        Returns:
            (PyDef): matching def
            (None): if no def found and catch used

        Raises:
            (ValueError): if exactly one matching child wasn't found
        """
        _filtered = get_single(self.find_defs(
            filter_=match, recursive=recursive), catch=True)
        if _filtered:
            return _filtered

        _exact_match = get_single(
            [
                _def for _def in self.find_defs(recursive=recursive)
                if _def.name == match],
            fail_message='Failed to find {} in {}'.format(
                match, self.py_file.path),
            catch=catch)
        if _exact_match:
            return _exact_match

        if catch:
            return None
        raise ValueError(match)

    def find_defs(self, filter_=None, recursive=False):
        """Find child defs of this object.

        Args:
            filter_ (str): apply filter to list of defs
            recursive (bool): also check children's children recursively
        """
        from psyhive.utils.py_file.def_ import PyDef

        _defs = [
            _item for _item in self.find_children(
                filter_=filter_, recursive=recursive)
            if isinstance(_item, PyDef)]
        return _defs

    def fix_docs(self, recursive=True):
        """Fix docs of this object.

        Args:
            recursive (bool): also fix children's children recursively
        """
        print 'FIX DOCS', self

        try:
            self.check_docs()
        except MissingDocs as _exc:
            _suggestion = self.get_docs_suggestion()
            copy_text(_suggestion)
            raise FileError(
                _exc.message, file_=self.py_file.path,
                line_n=self._ast.lineno+1)

        if recursive:
            for _child in self.find_children():
                _child.fix_docs()

    def get_docs_suggestion(self, verbose=0):
        """Get suggestion for this def's docstring.

        Args:
            verbose (int): print process data
        """

    def _get_ast(self):
        """Get this objects associated absract syntax tree object."""
        return self._ast

    @store_result_on_obj
    def _read_children(self, force=False, verbose=0):
        """Read children of this object (executed on init).

        Args:
            force (bool): force reread children
            verbose (int): print process data
        """
        from psyhive.utils.py_file.class_ import PyClass
        from psyhive.utils.py_file.def_ import PyDef
        from psyhive.utils.py_file.file_ import PyFile

        _ast = self._get_ast()
        _objs = []

        for _item in _ast.body:

            _name = getattr(_item, 'name', '-')
            if not isinstance(self, PyFile):
                _name = self.name+'.'+_name

            lprint("FOUND", _item, verbose=verbose)
            if isinstance(_item, ast.FunctionDef):
                _obj = PyDef(ast_=_item, py_file=self.py_file, name=_name)
            elif isinstance(_item, ast.ClassDef):
                _obj = PyClass(ast_=_item, py_file=self.py_file, name=_name)
            else:
                _obj = None

            if _obj:
                _objs.append(_obj)

        return _objs

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.name)
