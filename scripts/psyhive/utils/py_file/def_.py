"""Tools for managing python definitions."""

import ast
import copy
import operator

from psyhive.utils.cache import store_result_on_obj
from psyhive.utils.filter_ import apply_filter
from psyhive.utils.misc import to_nice, safe_zip, get_single, lprint

from psyhive.utils.py_file.arg import PyArg
from psyhive.utils.py_file.base import PyBase
from psyhive.utils.py_file.docs import PyDefDocs, MissingDocs


class PyDef(PyBase):
    """Represents a python definition."""

    def find_arg(self, filter_=None):
        """Find an arg belonging to this def.

        Args:
            filter_ (str): filter list of args
        """
        return get_single(self.find_args(filter_=filter_))

    def find_args(self, filter_=None):
        """Find args belonging to this def.

        Args:
            filter_ (str): filter list of args
        """
        return apply_filter(
            self._read_args(), filter_, key=operator.attrgetter('name'))

    def fix_docs(self, recursive=False):
        """Fix this def's docstrings.

        Args:
            recursive (bool): recursively fix child docs
        """
        super(PyDef, self).fix_docs(recursive=recursive)

    def get_docs(self):
        """Get this def's docs.

        Returns:
            (PyDefDocs): docs object
        """
        return PyDefDocs(ast.get_docstring(self._ast))

    def check_docs(self, recursive=False, verbose=0):
        """Check this def's docstring.

        Args:
            recursive (bool): recursively check child docs
            verbose (int): print process data
        """
        _docs = self.get_docs()

        # Some defs don't need docs
        if self.is_super_private and not self.clean_name == '__init__':
            return
        elif (  # Ignore ui callbacks
                self.clean_name.startswith('_redraw__') or
                self.clean_name.startswith('_callback__') or
                self.clean_name.startswith('_context__')
        ):
            return

        # Check header
        if not _docs.header:
            raise MissingDocs('No docs found')
        if not _docs.header.endswith('.'):
            raise MissingDocs('No trailing period in header')

        # Check args
        _ast_args = [
            _arg for _arg in self._ast.args.args
            if not _arg.id == 'self']
        for _ast_arg, _docs_arg in zip(_ast_args, _docs.args):
            lprint('CHECKING ARG', _ast_arg, _docs_arg, verbose=verbose)
            if not _ast_arg.id == _docs_arg.name:
                raise MissingDocs(
                    'Arg {} missing from docs'.format(_ast_arg.id))
            if not _docs_arg.type_:
                raise MissingDocs('Arg {} missing type'.format(_ast_arg.id))
            if not _docs_arg.desc:
                raise MissingDocs('Arg {} missing desc'.format(_ast_arg.id))
        if len(_ast_args) > len(_docs.args):
            raise MissingDocs('Docs are missing args')
        elif len(_ast_args) < len(_docs.args) and not self._ast.args.kwarg:
            raise MissingDocs('Docs have superfluous args')

    def get_docs_suggestion(self, verbose=0):
        """Get suggestion for this def's docstring.

        Args:
            verbose (int): print process data
        """
        _docs = self.get_docs()
        lprint('DOCS', _docs, verbose=verbose)
        if self.name.endswith('.__init__'):
            _header = 'Constructor.'
        else:
            _header = _docs.header or to_nice(self.clean_name)
        _indent = ' '*(self._ast.col_offset+4)

        _docs = '{}"""{}'.format(_indent, _header)

        # Add args
        _args = [_arg for _arg in self.find_args() if not _arg.name == 'self']
        if _args:
            _docs += '\n\n{}Args:\n'.format(_indent)
            for _arg in _args:
                lprint(' - ADDING ARG', _arg, _arg.type_, verbose=verbose)
                _arg_docs = _arg.get_docs()
                if _arg_docs:
                    _type = _arg_docs.type_
                    _desc = _arg_docs.desc
                elif _arg.name == 'verbose':
                    _type = 'int'
                    _desc = 'print process data'
                else:
                    _type = _arg.type_.__name__ if _arg.type_ else ''
                    _desc = ''
                _docs += '{}    {} ({}): {}\n'.format(
                    _indent, _arg.name, _type, _desc)
            _docs += _indent

        # Add returns
        if 'return ' in self.get_code():
            _docs = _docs.rstrip()
            _docs += (
                '\n\n{indent}Returns:\n{indent}    (): \n{indent}'.format(
                    indent=_indent))

        _docs += '"""\n'

        return _docs

    @store_result_on_obj
    def _read_args(self):
        """Find args on this def.

        Returns:
            (PyArg list): list of args
        """
        _defaults = copy.copy(self._ast.args.defaults)
        while len(_defaults) < len(self._ast.args.args):
            _defaults.insert(0, None)

        _args = []
        for _arg, _default in safe_zip(self._ast.args.args, _defaults):
            # print _arg.id
            _arg = PyArg(_arg, default=_default, def_=self)
            _args.append(_arg)

        return _args
