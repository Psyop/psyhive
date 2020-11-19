"""Tools for parsing/updating ma files without maya."""

from .cache import store_result_content_dependent, build_cache_fmt
from .path import File
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
    'relationship',  # connectAttr can be before and after
]


class _MaExprBase(object):
    """Base class for any top level ma file declaration."""

    def __init__(self, body):
        """Constructor.

        Args:
            body (str): declaration text
        """
        check_heart()
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
        return self.tokens[_idx]

    def __repr__(self):
        return '<{}:{}>'.format(
            type(self).__name__.strip('_'), self.name or self.type_)


class _MaExprCreateNode(_MaExprBase):
    """Represents a createNode declaration in an ma file."""

    def __init__(self, body):
        """Constructor.

        Args:
            body (str): declaration text body
        """
        super(_MaExprCreateNode, self).__init__(body)

        self.type = self.tokens[1]

        _name = self.read_flag('-n').strip('";')
        if '-p' in self.tokens:
            _parent = self.read_flag('-p').strip('";')
            _name = '{}|{}'.format(_parent, _name)
        self.name = _name


class _MaExprFile(_MaExprBase):
    """Represents a file declaration (eg. reference) in an ma file."""

    def __init__(self, body):
        """Constructor.

        Args:
            body (str): declaration text body
        """
        super(_MaExprFile, self).__init__(body)
        self.path = self.tokens[-1].strip('";')
        self.node = self.read_flag('-rfn')
        self.namespace = self.read_flag('-ns').strip('"')
        self.name = self.namespace


class MaFile(File):
    """Represents an ma file."""

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to ma file
        """
        super(MaFile, self).__init__(file_)
        self.body = self.read()

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
            type_ (str): filter by expression type

        Returns:
            (MaExprBase): matching expression
        """
        _exprs = self.find_exprs(type_=type_)
        assert _exprs
        return get_single(_exprs)

    def find_exprs(self, type_=None):
        """Search expressions in this file.

        Args:
            type_ (str): filter by expression type

        Returns:
            (MaExprBase list): matching expressions
        """
        _exprs = []
        for _expr in self._read_exprs():
            if type_ and _expr.type_ != type_:
                continue
            _exprs.append(_expr)
        return _exprs

    @store_result_content_dependent
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
        _expr_text = ''
        for _last, _line in qt.progress_bar(
                last(self.read_lines()), show=progress, stack_key='MaParse'):

            if not _line.strip() or _line.startswith('//'):
                continue

            if _line[0].isspace() and not _last:
                _expr_text += _line
                continue

            # Add expression to list
            if _expr_text:
                _type = _expr_text.split()[0]
                if _type not in _EXPR_ORDER:
                    raise ValueError(
                        'Unhandled ma file declaration '+_type)
                assert _expr_text.endswith(';')
                _expr_text = _expr_text.rstrip(';')
                _class = {
                    'file': _MaExprFile,
                    'createNode': _MaExprCreateNode,
                }.get(_type, _MaExprBase)
                _expr = _class(_expr_text)
                lprint(' - ADD EXPR', _expr, verbose=verbose)
                _exprs.append(_expr)

            _expr_text = _line

        lprint('FOUND {:d} EXPRS'.format(len(_exprs)), verbose=verbose)
        return _exprs

    @store_result_content_dependent
    def find_files(self):
        """Find file expressions (references) in this file.

        Returns:
            (MaExprBase list): matching expressions
        """
        return self.find_exprs(type_='file')

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
