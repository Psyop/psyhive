"""Base class for any python component."""

import ast
import operator

from ..filter_ import apply_filter
from ..cache import store_result_on_obj
from ..misc import copy_text, lprint, get_single
from ..path import FileError

from .docs import MissingDocs


class PyBase(object):
    """Base class for any component of a python file."""

    docs = None

    def __init__(self, ast_, py_file, name=None, read_docs=True):
        """Constructor.

        Args:
            ast_ (ast.Module): ast module for this object
            py_file (PyFile): parent python file for this object
            name (str): override name for this object
            read_docs (bool): read docstring from ast
        """
        from .file_ import PyFile
        assert isinstance(py_file, PyFile)

        self._ast = ast_
        if read_docs and self._ast:
            self.docs = ast.get_docstring(self._ast)
        self.py_file = py_file
        self.name = name or ast_.name

        self.clean_name = name.split('.')[-1]
        self.is_super_private = self.clean_name.startswith('__')
        self.is_private = self.clean_name.startswith('_')

        self.cmp_str = '{}:{}'.format(self.py_file.path, self.name)

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
            private=None, force=False):
        """Find child node of this object.

        Args:
            match (str): filter or exact match string
            recursive (bool): recurse into children's children
            catch (bool): no error on fail to find
            type_ (PyBase): filter by object type
            private (bool): filter by private/non-private
            force (bool): rebuild list of children from file

        Returns:
            (PyBase): matching child object

        Raises:
            (ValueError): if search did not match exactly one child
        """

        # Try match as filter
        _filtered = get_single(
            self.find_children(
                filter_=match, recursive=recursive, type_=type_,
                private=private, force=force),
            catch=True)
        if _filtered:
            return _filtered

        # Try match as exact name match
        _children = self.find_children(recursive=recursive, type_=type_)
        _exact_match = get_single(
            [_child for _child in _children if _child.name == match],
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
        from .def_ import PyDef
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
        from .def_ import PyDef
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

    def get_code(self, docs=True):
        """Get code for this object.

        Args:
            docs (bool): include docstrings

        Returns:
            (str): python code
        """
        _this = self.py_file.find_child(self.name, recursive=True)
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
        _code = '\n'.join(self.py_file.read().split('\n')[_start: _end])

        # Remove docs
        if not docs and self.docs:
            _splitter = '"""'
            if not _code.count(_splitter):
                _splitter = "'''"
            if not _code.count(_splitter):
                print _code
                raise RuntimeError
            _tokens = _code.split(_splitter)
            _code = _tokens[0] + _splitter.join(_tokens[2:])

        return _code

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

    def _read_child(self, ast_item, verbose=0):
        """Convert an ast object to a PyBase object.

        If the object cannot be converted, nothing is returned.

        This is implemented as a separate method to allow the PyFile
        object to be sublclassed and additional dynamics PyBase objects
        to be added (for example to allow matching of section declarations
        in py_gui objectes).

        Args:
            ast_item (ast.Module): ast object to convert
            verbose (int): print process data

        Returns:
            (PyBase|None): def/class object (if any)
        """
        from .class_ import PyClass
        from .def_ import PyDef
        from .file_ import PyFile

        _name = getattr(ast_item, 'name', '-')
        if not isinstance(self, PyFile):
            _name = self.name+'.'+_name

        lprint("FOUND", ast_item, verbose=verbose)
        if isinstance(ast_item, ast.FunctionDef):
            _obj = PyDef(ast_=ast_item, py_file=self.py_file, name=_name)
        elif isinstance(ast_item, ast.ClassDef):
            _obj = PyClass(ast_=ast_item, py_file=self.py_file, name=_name)
        else:
            _obj = None

        return _obj

    @store_result_on_obj
    def _read_children(self, force=False):
        """Read children of this object (executed on init).

        Args:
            force (bool): force reread children
        """
        _ast = self.get_ast(force=force)

        _objs = []
        for _item in _ast.body:
            _obj = self._read_child(ast_item=_item)
            if _obj:
                _objs.append(_obj)

        return _objs

    def __cmp__(self, other):
        return cmp(self.cmp_str, other.cmp_str)

    def __hash__(self):
        return hash(self.cmp_str)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.name)
