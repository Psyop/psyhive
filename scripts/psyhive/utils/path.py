"""Tools for managing paths in a file structure."""

import filecmp
import functools
import os
import shutil
import six

from psyhive.utils.misc import lprint, system, dprint, bytes_to_str
from psyhive.utils.heart import check_heart
from psyhive.utils.filter_ import passes_filter

TMP = 'W:/Temp'


def restore_cwd(func):
    """Decorator to restore cwd after executing a function.

    Args:
        func (fn): function to decorate
    """

    @functools.wraps(func)
    def _restore_cwd_fn(*args, **kwargs):
        _cwd = os.getcwd()
        _result = func(*args, **kwargs)
        os.chdir(_cwd)
        return _result

    return _restore_cwd_fn


class FileError(RuntimeError):
    """Raises when a file causes an issue."""

    def __init__(self, message, file_, line_n=None):
        """Constructor.

        Args:
            message (str): error message
            file_ (str): path to file
            line_n (int): line of file causing issue
        """
        super(FileError, self).__init__(message)
        self.file_ = file_
        self.line_n = line_n


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
        """Get absolute value of this path."""
        return abs_path(self.path)

    def exists(self):
        """Check whether this path exists."""
        return os.path.exists(self.path)

    def get_size(self):
        """Get size of this path.

        Returns
            (int): size of path in bytes
        """
        return os.path.getsize(self.path)

    def parent(self):
        """Get parent dir of this path.

        Returns:
            (Dir): parent
        """
        return Dir(os.path.dirname(self.path))

    def rel_path(self, path):
        """Get relative path of the given path from this path.

        Args:
            path (str): path to compare
        """
        return rel_path(root=self.path, path=path)

    def __cmp__(self, other):
        return cmp(self.path, other.path)

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        return '<{}|{}>'.format(type(self).__name__.strip('_'), self.path)


class Dir(Path):
    """Represents a directory on disk."""

    def find(self, **kwargs):
        """Search for files in this dir.

        Returns:
            (str list): list of files
        """
        return find(self.path, **kwargs)

    @restore_cwd
    def launch_browser(self):
        """Launch browser set to this dir."""
        print 'LAUNCH BROWSER'
        os.chdir(self.path)
        system('explorer .', verbose=1)


class File(Path):
    """Represents a file on disk."""

    def edit(self, line_n=None, verbose=0):
        """Edit this file in a text editor.

        Args:
            line_n (int): line of the file to open
            verbose (int): print process data
        """
        _path = self.path
        if line_n:
            _path += ':{:d}'.format(line_n)
        _cmds = [
            r'C:\Program Files\Sublime Text 3\subl.exe',
            _path]

        system(_cmds, verbose=verbose)

    def read(self):
        """Read the text contents of this file."""
        return read_file(self.path)


def abs_path(path, win=False, root=None, verbose=0):
    """Get the absolute path for the given path.

    Args:
        path (str): path to check
        win (bool): format for windows using escape chars
        root (str): override root dir (otherwise cwd is used)
        verbose (int): print process data
    """
    if not isinstance(path, six.string_types):
        raise ValueError(path)
    _path = path
    lprint('USING PATH', _path, verbose=verbose)

    # Handle file:/// prefix
    if _path.startswith('file:///'):
        _path = _path[8:]

    # Handle relative paths
    if _path.startswith('~/'):
        _path = '{}/{}'.format(os.environ['HOME'], _path[2:])
    elif not (_path.startswith('/') or _path[1] == ':'):
        _root = root or os.getcwd()
        lprint('ADDING ROOT', _root, verbose=verbose)
        _path = '{}/{}'.format(_root, _path)

    _path = _path.\
        replace('\\\\', '/').\
        replace('\\', '/').\
        replace('//', '/').\
        replace('/./', '/').\
        replace('c:/users/hvande~1', 'C:/users/hvanderbeek')
    lprint('CLEANED', _path, verbose=verbose)

    # Fix embedded relative dir up
    while '../' in _path:
        check_heart()
        _tokens = _path.split("/")
        _idx = _tokens.index('..')
        _tokens.pop(_idx)
        _tokens.pop(_idx-1)
        _path = '/'.join(_tokens)

    if win:
        return _path.replace('/', '\\')
    return _path


def diff(left, right):
    """Show diffs between two files.

    Args:
        left (str): path to left file
        right (str): path to right file
    """
    print "FILECMP"
    assert not filecmp.cmp(left, right)

    _bcomp_exe = 'C:/Program Files/Beyond Compare 4/BComp.exe'
    system([_bcomp_exe, left, right], verbose=1)


def find(
        dir_=None, type_=None, extn=None, filter_=None, base=None, depth=-1,
        name=None, full_path=True, verbose=0):
    """Find files/dirs in a given path.

    Args:
        dir_ (str): override root path
        type_ (str): filter by path type (f=files, d=dirs, l=links)
        extn (str): filter by extension
        filter_ (str): apply filter to the list
        base (str): filter by file basename
        depth (int): max dir depth to traverse (-1 means unlimited)
        name (str): match exact file/dir name
        full_path (bool): return full path to file
        verbose (int): print process data
    """
    _kwargs = locals()
    _kwargs.pop('dir_')
    _kwargs.pop('depth')
    _kwargs.pop('full_path')

    _results = []
    _dir = abs_path(dir_ or os.getcwd())

    # Get a list of files in dir
    try:
        _files = os.listdir(_dir)
    except WindowsError:
        _files = []

    for _file in _files:

        _path = abs_path('{}/{}'.format(_dir, _file))
        lprint('TESTING', _path, _file, verbose=verbose)

        # Recurse into subdirs
        _is_dir = os.path.isdir(_path)
        if _is_dir:
            _depth = max(depth - 1, -1)
            if _depth:
                _results += find(_path, depth=_depth, **_kwargs)

        # Apply type filter
        if type_ is None:
            pass
        elif type_ == 'd':
            if not _is_dir:
                continue
        elif type_ == 'f':
            if not os.path.isfile(_path):
                lprint(' - NOT FILE', verbose=verbose)
                continue
        elif type_ == 'l':
            if not os.path.islink(_path):
                continue
        elif type_:
            raise ValueError(type_)

        # Apply extn filter
        if extn and not Path(_path).extn == extn:
            lprint(' - BAD EXTN', verbose=verbose)
            continue

        # Apply base filter
        if base and not _file.startswith(base):
            continue

        # Apply filter
        if filter_ and not passes_filter(_path, filter_):
            lprint(' - FILTERED', verbose=verbose)
            continue

        if name and not _file == name:
            lprint(' - NAME FILTER', verbose=verbose)
            continue

        _results.append(_path)

    if not full_path:
        _results = [
            _result.replace(_dir+'/', '') for _result in _results]

    return sorted(_results)


def nice_size(path):
    """Get the size on disk of the given path in a readable format.

    Args:
        path (str): path to read size of

    Returns:
        (str): size as a string
    """
    _size = os.path.getsize(path)
    return bytes_to_str(_size)


def read_file(file_):
    """Read the contents of the given file.

    Args:
        file_ (str): path to check
    """
    _file = open(file_, 'r')
    _text = _file.read()
    _file.close()
    return _text


def read_yaml(file_):
    """Read contents of given yaml file.

    Args:
        file_ (str): path to read
    """
    import yaml
    if not os.path.exists(file_):
        raise OSError('Missing file '+file_)
    _body = read_file(file_)
    return yaml.load(_body)


def replace_file(source, replace, force=False):
    """Replace a file with the given source file.

    By default this will shows a diff and then raise a confirmation dialog.

    Args:
        source (str): path to source file
        replace (str): path to file to replace
        force (bool): supress diff and confirmation
    """
    from psyhive import qt

    print source, replace
    if not force:
        diff(source, replace)
        qt.ok_cancel(
            'Replace file with source?\n\nSource:\n\n{}'
            '\n\nReplace:\n\n{}'.format(
                source, replace))
    shutil.copy(source, replace)


def rel_path(path, root):
    """Get the relative path of the given path from the given root.

    Args:
        path (str): path to test
        root (str): base path to test against

    Returns:
        (str): relative path

    Raises:
        (ValueError): if path is not inside root
    """
    _path = abs_path(path)
    _root = abs_path(root)
    if not _path.startswith(_root):
        raise ValueError
    return _path[len(_root):].lstrip('/')


def search_files_for_text(
        files, text=None, filter_=None, win=False, edit=False, verbose=0):
    """Search the contents of the given files for text.

    Args:
        files (str list): list of files to check
        text (str): text to match in each line
        filter_ (str): apply filter to each line
        win (bool): display paths in windows format
        edit (bool): open the first found instance in an editor and exit
        verbose (int): print process data
    """
    from psyhive import qt

    _found_instance = False
    for _file in qt.ProgressBar(
            files, 'Searching {:d} file{}', col='Aquamarine', show=not edit):

        dprint('CHECKING FILE', _file, verbose=verbose)

        _printed_path = False
        for _idx, _line in enumerate(read_file(_file).split('\n')):

            # Check if this line should be printed
            _print_line = False
            if text and text in _line:
                _print_line = True
            elif filter_ and passes_filter(
                    _line, filter_, case_sensitive=True):
                _print_line = True

            if _print_line:
                if not _printed_path:
                    lprint(abs_path(_file, win=win))
                lprint('{:>6} {}'.format('[{:d}]'.format(_idx+1), _line))
                _printed_path = True
                _found_instance = True
                if edit:
                    File(_file).edit(line_n=_idx+1)
                    return

        if _printed_path:
            lprint()

    if not _found_instance:
        dprint('No instances found')


def test_path(dir_):
    """Test the given path exists as a dir.

    Args:
        dir_ (str): path to test
    """
    if os.path.exists(dir_) and os.path.isdir(dir_):
        return
    os.makedirs(dir_)


def touch(file_):
    """Make an empty file at the given path.

    Args:
        file_ (str): path to create
    """
    _path = abs_path(file_)
    if not os.path.exists(_path):
        test_path(os.path.dirname(_path))
        write_file(file_=_path, text='')


def write_file(file_, text, force=False):
    """Write the given text to the given file path.

    Args:
        file_ (str): path to write to
        text (str): text to write
        force (bool): overwrite any existing file with no warning
    """
    if os.path.exists(file_):
        if not force:
            from psyhive import qt
            qt.ok_cancel('Overwrite file?\n\n'+file_)
        os.remove(file_)

    _file = open(file_, 'w')
    _file.write(text)
    _file.close()


def write_yaml(file_, data):
    """Write yaml data to file.

    Args:
        file_ (str): path to yaml file
        data (dict): data to write to yaml
    """
    import yaml
    test_path(os.path.dirname(file_))
    with open(file_, 'w') as _file:
        yaml.dump(data, _file, default_flow_style=False)
