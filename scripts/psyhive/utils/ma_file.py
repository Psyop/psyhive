"""Tools for parsing/updating ma files without maya."""

import os

from .cache import (
    store_result_content_dependent, build_cache_fmt, store_result)
from .path import File, FileError
from .heart import check_heart
from .misc import get_single, lprint, last

_EXPR_ORDER = [
    'file',
    'currentUnit',
    'fileInfo',
    'requires',
    'createNode',
    'lockNode',
    'select',
    'connectAttr',
    'relationship',  # connectAttr can be before and after relationship
    'dataStructure',
]


class _MaExprBase(object):
    """Base class for any top level ma file declaration."""

    def __init__(self, body, parent):
        """Constructor.

        Args:
            body (str): declaration text
            parent (MaFile): parent ma file
        """
        check_heart()
        self.parent = parent
        self.body = body
        self.tokens = body.split()
        self.type_ = self.tokens[0]
        self.name = None

    def read_flag(self, flag):
        """Read the given flag from this declaration's text.

        This find the first instance of the tag and then returns
        the next token.

        Args:
            flag (str): flag to read (eg. -ftn)

        Returns:
            (str): corresponding token
        """
        assert flag in self.tokens
        _idx = self.tokens.index(flag) + 1
        return self.tokens[_idx].strip('"').strip(';')

    def __repr__(self):
        return '<{}:{}>'.format(
            type(self).__name__.strip('_'), self.name or self.type_)


class _MaExprCreateNode(_MaExprBase):
    """Represents a createNode declaration in an ma file."""

    def __init__(self, body, parent):
        """Constructor.

        Args:
            body (str): declaration text body
            parent (MaFile): parent ma file
        """
        super(_MaExprCreateNode, self).__init__(body=body, parent=parent)

        self.node_type = self.tokens[1]
        # assert not self.type_ == 'createNode'

        _name = self.read_flag('-n')
        if '-p' in self.tokens:
            _parent = self.read_flag('-p')
            _name = '{}|{}'.format(_parent, _name)
        self.name = _name


class _MaExprFile(_MaExprBase):
    """Represents a file declaration (eg. reference) in an ma file."""

    def __init__(self, body, parent):
        """Constructor.

        Args:
            body (str): declaration text body
            parent (MaFile): parent ma file
        """
        super(_MaExprFile, self).__init__(body=body, parent=parent)
        self.path = self.tokens[-1].strip(';"')
        self.node = self.read_flag('-rfn')
        self.namespace = self.read_flag('-ns')
        self.name = self.namespace

    def set_path(self, file_):
        """Set file path for this expression.

        Args:
            file_ (str): path to update to
        """
        assert os.path.exists(file_)
        assert self.body.count(self.path) == 1
        _new_body = self.body.replace(self.path, file_)
        self.parent.update_expr(self.body, _new_body)


class MaFile(File):
    """Represents an ma file."""

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to ma file
        """
        super(MaFile, self).__init__(file_)
        self.body = self.read()
        self._new_body = None
        if not self.extn == 'ma':
            raise ValueError('Bad extn '+self.extn)

    def update_expr(self, cur_expr, new_expr):
        """Update the given expression for a new one.

        Args:
            cur_expr (MaExprBase): expression to replace
            new_expr (MaExprBase): expression to replace with
        """
        self._new_body = self._new_body or self.body
        assert self._new_body.count(cur_expr) == 1
        self._new_body = self._new_body.replace(cur_expr, new_expr)

    @property
    def cache_fmt(self):
        """Get cache format path.

        Returns:
            (str): cache format
        """
        return build_cache_fmt(self.path, level='project')

    def find_expr(self, type_):
        """Find a single expression in this file.

        Args:
            type_ (str): match expression type

        Returns:
            (MaExprBase): matching expression
        """
        _exprs = self.find_exprs(type_=type_)
        assert _exprs
        return get_single(_exprs)

    def find_exprs(self, type_=None):
        """Search expressions in this file.

        Args:
            type_ (str): match expression type

        Returns:
            (MaExprBase list): matching expressions
        """
        _exprs = []
        for _expr in self._read_exprs():
            if type_ and _expr.type_ != type_:
                continue
            _exprs.append(_expr)
        return _exprs

    @store_result
    def _read_exprs(self, progress=False, verbose=0):
        """Read expressions in this ma file.

        Args:
            progress (bool): show progress bar
            verbose (int): print process data

        Returns:
            (MaExprBase list): matching expressions
        """
        from psyhive import qt

        _exprs = []
        _expr_lines = []
        for _idx, (_last, _line) in qt.progress_bar(
                enumerate(last(self.read_lines())),
                show=progress, stack_key='MaParse'):

            if not _line.strip() or _line.startswith('//'):
                continue

            if _line[0].isspace() and not _last:
                _expr_lines.append(_line)
                continue

            # Add expression to list
            if _expr_lines:
                _type = _expr_lines[0].split()[0]
                if _type not in _EXPR_ORDER:
                    raise FileError(
                        'Unhandled ma file declaration '+_type,
                        line_n=_idx, file_=self.path)
                _expr_text = '\n'.join(_expr_lines)
                _expr_text = _expr_text.strip()
                assert _expr_text.endswith(';')
                _class = {
                    'file': _MaExprFile,
                    'createNode': _MaExprCreateNode,
                }.get(_type, _MaExprBase)
                _expr = _class(_expr_text, parent=self)
                lprint(' - ADD EXPR', _expr, verbose=verbose)
                _exprs.append(_expr)

            _expr_lines = [_line]

        lprint('FOUND {:d} EXPRS'.format(len(_exprs)), verbose=verbose)
        return _exprs

    def find_create_nodes(self, force=False, type_=None):
        """Find file expressions (references) in this file.

        Args:
            force (bool): force reread expressions from disk
            type_ (str): match node type

        Returns:
            (MaExprBase list): matching expressions
        """
        _nodes = self._read_create_nodes(force=force)
        if type_:
            _nodes = [_node for _node in _nodes if _node.node_type == type_]
        return _nodes

    def find_files(self, force=False, node=None, namespace=None):
        """Find file expressions (references) in this file.

        Args:
            force (bool): force reread expressions from disk
            node (str): match node name
            namespace (str): match referemce namespace

        Returns:
            (MaExprBase list): matching expressions
        """
        _files = self._read_files(force=force)
        if node:
            _files = [_file for _file in _files if _file.node == node]
        if namespace:
            _files = [_file for _file in _files
                      if _file.namespace == namespace]
        return _files

    @store_result_content_dependent
    def find_fps(self):
        """Find fps for this ma file.

        Returns:
            (float): frame rate
        """
        _unit = self.find_expr('currentUnit')
        _time = _unit.read_flag('-t')
        return {'pal': 25.0,
                'ntsc': 30.0,
                'film': 24.0}[_time]

    def find_refs(self, force=False):
        """Find references in this ma file.

        It seems like each reference has two expressions associated with it;
        this will only return the last one.

        Args:
            force (bool): force reread expressions from disk

        Returns:
            (MaExprFile): list of file expressions
        """
        _refs = {}
        for _file in self.find_files(force=force):
            _refs[_file.namespace] = _file
        return sorted(_refs.values())

    @store_result_content_dependent
    def _read_create_nodes(self, force=False):
        """Find file expressions (references) in this file.

        Args:
            force (bool): force reread expressions from disk

        Returns:
            (MaExprCreateNode list): matching expressions
        """
        return self.find_exprs(type_='createNode')

    @store_result_content_dependent
    def _read_files(self, force=False):
        """Find file expressions (references) in this file.

        Args:
            force (bool): force reread expressions from disk

        Returns:
            (MaExprFile list): matching expressions
        """
        return self.find_exprs(type_='file')

    def save_as(self, file_, force=False):
        """Save updated version of this file at the given path.

        Args:
            file_ (str): path to save at
            force (bool): overwrite without warning
        """
        assert self._new_body
        File(file_).write_text(self._new_body, force=force)
