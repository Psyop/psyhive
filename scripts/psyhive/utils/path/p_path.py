"""Tools for managing the path object."""

import os
import time

from ..misc import get_ord, nice_age


class Path(object):
    """Represents a path on disk."""

    def __init__(self, path, extn=None):
        """Constructor.

        Args:
            path (str): path in file structure
            extn (str): override extension (eg. tar.gz)
        """
        self.path = path
        self.dir = os.path.dirname(path)
        self.filename = os.path.basename(path)
        if extn:
            assert self.filename.endswith('.'+extn)
            self.extn = extn
            self.basename = self.filename[:-len(extn)-1]
        elif '.' in self.filename:
            _tokens = self.filename.split('.')
            self.extn = _tokens[-1]
            self.basename = '.'.join(_tokens[:-1])
        else:
            self.extn = None
            self.basename = self.filename

    def abs_path(self):
        """Get absolute value of this path.

        Returns:
            (str): abs path
        """
        from .p_tools import abs_path
        return abs_path(self.path)

    def exists(self):
        """Check whether this path exists.

        Returns:
            (bool): whether file exists
        """
        return os.path.exists(self.path)

    def get_age(self):
        """Get age of this file (based on mtime).

        Returns:
            (float): age in seconds
        """
        return time.time() - self.get_mtime()

    def get_mtime(self):
        """Get mtime of this path.

        Returns:
            (float): mtime
        """
        return os.path.getmtime(self.path)

    def get_size(self):
        """Get size of this path.

        Returns
            (int): size of path in bytes
        """
        return os.path.getsize(self.path)

    def is_file(self):
        """Test if this path is a file.

        Returns:
            (bool): whether file
        """
        return os.path.isfile(self.path)

    def nice_age(self):
        """Get this file's age as a readable string.

        Returns:
            (str): age as string
        """
        return nice_age(self.get_age())

    def nice_mtime(self, fmt=None):
        """Get mtime of this file in a readable format.

        Args:
            fmt (str): override strftime format

        Returns:
            (str): mtime as readable string
        """
        _mtime = self.get_mtime()
        _mtime_t = time.localtime(_mtime)
        if fmt:
            _fmt = fmt
        else:
            _month = int(time.strftime('%d', _mtime_t))
            _ord = get_ord(_month)
            _day = '{:d}{}'.format(_month, _ord)
            _fmt = '%a {} %Y %b %H:%M:%S'.format(_day)
        return time.strftime(_fmt, _mtime_t)

    def nice_size(self):
        """Get size of this path as a readable str.

        Returns
            (str): readable size of path
        """
        from .p_tools import nice_size
        return nice_size(self.path)

    def parent(self):
        """Get parent dir of this path.

        Returns:
            (Dir): parent
        """
        from .p_dir import Dir
        return Dir(os.path.dirname(self.path))

    def rel_path(self, path):
        """Get relative path of the given path from this path.

        Args:
            path (str): path to compare
        """
        from .p_tools import rel_path
        return rel_path(root=self.path, path=path)

    def __cmp__(self, other):
        if hasattr(other, 'path'):
            return cmp(self.path, other.path)
        return cmp(self.path, other)

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        return '<{}|{}>'.format(type(self).__name__.strip('_'), self.path)
