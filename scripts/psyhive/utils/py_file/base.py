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

        self.clean_name = name.split('.')[-1]
        self.is_super_private = self.clean_name.startswith('__')
        self.is_private = self.clean_name.startswith('_')

    def check_docs(self, recursive=False, verbose=0):
        """Check this object's docstring.

        (To be implemented in subclass)

        Args:
            recursive (bool): recursively check child docs
            verbose (int): print process data
        """

    def edit(self):
        """Open this component in a editor."""
        self.py_file.edit(line_n=self._ast.lineno)

    def find_child(
            self, match=None, recursive=False, catch=False, type_=None,
            private=None):
        """Find child node of this object.

        Args:
            match (str): filter or exact match string
            recursive (bool): recurse into children's children
            catch (bool): no error on fail to find
            type_ (PyBase): filter by object type
            private (bool): filter by private/non-private

        Returns:
            (PyBase): matching child object

        Raises:
            (ValueError): if search did not match exactly one child
        """

        # Try match as filter
        _filtered = get_single(
            self.find_children(
                filter_=match, recursive=recursive, type_=type_,
                private=private),
            catch=True)
        if _filtered:
            return _filtered

        # Try match as exact name match
        _exact_match = get_single(
            [
                _child for _child in self.find_children(
                    recursive=recursive, type_=type_)
                if _child.name == match],
            fail_message='Failed to find {} in {}'.format(
                match, self.py_file.path),
            catch=catch)
        if _exact_match:
            return _exact_match

        # Handle fail
        if catch:
            return None
        raise ValueError(match)

    def find_children(
            self, filter_=None, recursive=False, force=False, type_=None,
            private=None):
        """Find children of this object.

        Args:
            filter_ (str): apply filter to list of children
            recursive (bool): also check children's children recursively
            force (bool): force reread ast from disk
            type_ (PyBase): filter by type
            private (bool): filter by private/non-private
        """
        if not recursive:
            _children = self._read_children(force=force)
        else:
            _children = []
            for _child in self._read_children(force=force):
                _children.append(_child)
                _children += _child.find_children(recursive=True)

        if type_:
            _children = [
                _child for _child in _children if isinstance(_child, type_)]

        if private is not None:
            _children = [
                _child for _child in _children if _child.is_private == private]

        if filter_:
            _children = apply_filter(
                _children, filter_, key=operator.attrgetter('name'))

        return _children

    def find_def(self, match=None, recursive=False, catch=False, private=None):
        """Find child def.

        Args:
            match (str): def name to search for
            recursive (bool): also check children's children recursively
            catch (bool): no error on fail to find def
            private (bool): filter by private/non-private

        Returns:
            (PyDef): matching def
            (None): if no def found and catch used

        Raises:
            (ValueError): if exactly one matching child wasn't found
        """
        from psyhive.utils.py_file.def_ import PyDef
        return self.find_child(
            match=match, recursive=recursive, catch=catch, type_=PyDef,
            private=private)

    def find_defs(self, filter_=None, recursive=False, private=None):
        """Find child defs of this object.

        Args:
            filter_ (str): apply filter to list of defs
            recursive (bool): also check children's children recursively
            private (bool): filter by private/non-private

        Returns:
            (PyDef list): list of matching defs
        """
        from psyhive.utils.py_file.def_ import PyDef
        return self.find_children(
            filter_=filter_, recursive=recursive, type_=PyDef,
            private=private)

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

    def get_code(self):
        """Get code for this object.

        Returns:
            (str): python code
        """
        _this = self.py_file.find_def(self.name, recursive=True)
        _children = [
            _child for _child in self.py_file.find_children(recursive=True)
            if not _child.name.startswith(_this.name+'.')]
        assert _this in _children
        _start = _this.get_ast().lineno - 1
        if _this == _children[-1]:
            _end = -1
        else:
            _next = _children[_children.index(_this)+1]
            assert not _next.name.startswith(_this.name+'.')
            _end = _next.get_ast().lineno - 1
        return '\n'.join(self.py_file.read().split('\n')[_start: _end])

    def get_docs_suggestion(self, verbose=0):
        """Get suggestion for this def's docstring.

        Args:
            verbose (int): print process data
        """

    def get_ast(self, force=False):
        """Get this objects associated absract syntax tree object.

        Args:
            force (bool): provided for symmetry

        Returns:
            (ast.Module): this object's syntax tree
        """
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

        _ast = self.get_ast(force=force)
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
