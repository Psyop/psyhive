"""Tools for managing paths in a file structure."""

import filecmp
import functools
import os
import shutil
import time

import ctypes
from ctypes import wintypes

import six

from psyhive.utils.misc import (
    lprint, system, dprint, bytes_to_str, copy_text, get_ord)
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
        """Get absolute value of this path.

        Returns:
            (str): abs path
        """
        return abs_path(self.path)

    def exists(self):
        """Check whether this path exists.

        Returns:
            (bool): whether file exists
        """
        return os.path.exists(self.path)

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
        return nice_size(self.path)

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
        if hasattr(other, 'path'):
            return cmp(self.path, other.path)
        return cmp(self.path, other)

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

    def test_path(self):
        """Test this dir exists, creating if needed."""
        test_path(self.path)


class File(Path):
    """Represents a file on disk."""

    def apply_extn(self, extn):
        """Update this file path with a different extension.

        Args:
            extn (str): new extension

        Returns:
            (File): new file path
        """
        return File('{}/{}.{}'.format(self.dir, self.basename, extn))

    def copy_to(self, file_):
        """Copy this file to another location.

        Args:
            file_ (str): target path
        """
        from psyhive import qt
        test_path(os.path.dirname(file_))
        if os.path.exists(file_):
            qt.ok_cancel("Replace existing file?\n\n"+file_)
        shutil.copy(self.path, file_)

    def delete(self, force=False):
        """Delete this file.

        Args:
            force (bool): delete with no confirmation
        """
        if not self.exists():
            return
        if not force:
            from psyhive import qt
            qt.ok_cancel("Delete file?\n\n"+self.path)
        os.remove(self.path)

    def diff(self, other, label=None, check_extn=True):
        """Show diffs between this and another text file.

        Args:
            other (str): path to other file
            label (str): pass label to diff app
            check_extn (bool): check extension is approved (to avoid
                binary compares)
       """
        diff(self.path, other, label=label, check_extn=check_extn)

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
        _cmds = ['subl', _path]

        system(_cmds, verbose=verbose)

    def is_writable(self):
        """Check if this path is writable.

        Returns:
            (bool): writable status
        """
        return os.access(self.path, os.W_OK)

    def read(self):
        """Read the text contents of this file."""
        return read_file(self.path)

    def read_lines(self):
        """Read text lines of this file.

        Returns:
            (str list): list of lines
        """
        return self.read().split('\n')

    def set_writable(self, writable=True):
        """Set writable state of this path.

        Args:
            writable (bool): writable state
        """
        _perms = 0o777 if writable else 0o444
        os.chmod(self.path, _perms)

    def test_dir(self):
        """Test this file's parent directory exists."""
        test_path(self.dir)

    def touch(self):
        """Touch this path."""
        touch(self.path)

    def write_text(self, text, force=False):
        """Write text to this file.

        Args:
            text (str): text to write
            force (bool): overwrite existing file with no warning
        """
        write_file(file_=self.path, text=text, force=force)


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
    _path = str(path)
    lprint('USING PATH', _path, verbose=verbose)

    # Handle file:/// prefix
    if _path.startswith('file:///'):
        _path = _path[8:]

    # Handle relative paths
    if _path.startswith('~/'):
        _path = '{}/{}'.format(os.environ['HOME'], _path[2:])
    elif not (
            _path.startswith('/') or
            (len(_path) >= 2 and _path[1] == ':')):
        _root = root or os.getcwd()
        lprint('ADDING ROOT', _root, verbose=verbose)
        _path = '{}/{}'.format(_root, _path)

    # Unify different dir separators
    _path = _path.\
        replace('\\\\', '/').\
        replace('\\', '/').\
        replace('//', '/').\
        replace('/./', '/').\
        replace('c:/users/hvande~1', 'C:/users/hvanderbeek')
    lprint('CLEANED', _path, verbose=verbose)

    # Fix MINGW64 style single drive letters with leading /
    _tokens = _path.split('/')
    if len(_tokens) > 1 and len(_tokens[1]) == 1:
        _path = '/'.join([_tokens[1]+':']+_tokens[2:])

    # Fix embedded relative dir up
    while '../' in _path:
        check_heart()
        _tokens = _path.split("/")
        _idx = _tokens.index('..')
        _tokens.pop(_idx)
        _tokens.pop(_idx-1)
        _path = '/'.join(_tokens)

    # Capitalise drive letter
    if len(_path) >= 2 and _path[1] == ':':
        _path = _path[0].upper() + _path[1:]

    if win:
        return _path.replace('/', '\\')
    return _path


def diff(left, right, tool=None, label=None, check_extn=True):
    """Show diffs between two files.

    Args:
        left (str): path to left file
        right (str): path to right file
        tool (str): diff tool to use
        label (str): label to pass to diff tool
        check_extn (bool): check extension is approved (to avoid
            binary compares)
    """
    _tool = tool or os.environ.get('PSYHIVE_DIFF_EXE') or 'Diffinity'
    if filecmp.cmp(left, right):
        raise RuntimeError("Files are identical")
    if check_extn and not File(left).extn in [
            None, 'py', 'yml', 'ui', 'nk', 'json']:
        raise ValueError(File(left).extn)
    _cmds = [_tool, left, right]
    if label and _tool == 'Meld':
        _cmds += ['-L', '"{}"'.format(label)]
    system(_cmds, verbose=1)


def _find_cast_results_by_class(results, class_):
    """Cast find results to the given class.

    Any that raise ValueError are ignored.

    Args:
        results (str list): list of result to cast
        class_ (type): type to cast to

    Returns:
        (list): castest results
    """
    _class_results = []
    for _result in results:
        try:
            _result = class_(_result)
        except ValueError:
            continue
        _class_results.append(_result)
    return _class_results


def find(
        dir_=None, type_=None, extn=None, filter_=None, base=None, depth=-1,
        name=None, full_path=True, class_=None, verbose=0):
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
        class_ (type): cast results to this type
        verbose (int): print process data

    Returns:
        (str list): paths found
    """
    _kwargs = locals()
    _kwargs.pop('dir_')
    _kwargs.pop('depth')
    _kwargs.pop('full_path')
    _kwargs.pop('class_')

    _results = []
    _dir = abs_path(dir_ or os.getcwd())

    if extn and extn.startswith('.'):
        raise ValueError("Extn should not start with period - "+extn)

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

        # Apply filters
        if not _find_path_passes_filters(
                path=_path, is_dir=_is_dir, type_=type_, name=name,
                filter_=filter_, base=base, extn=extn):
            continue

        _results.append(_path)

    if not full_path:
        _results = [
            _result.replace(_dir+'/', '') for _result in _results]

    # Apply class cast
    if class_:
        _results = _find_cast_results_by_class(
            results=_results, class_=class_)

    return sorted(_results)


def _find_path_passes_filters(path, is_dir, type_, extn, base, filter_,
                              name, verbose=0):
    """Test if a path passes find filters.

    Args:
        path (str): path to test
        is_dir (bool): whether path is a dir
        type_ (str): filter by path type (f=files, d=dirs, l=links)
        extn (str): filter by extension
        base (str): filter by file basename
        filter_ (str): apply filter to the list
        name (str): match exact file/dir name
        verbose (int): print process data

    Returns:
        (bool): whether path passes filters
    """

    # Apply type filter
    if type_ is None:
        pass
    elif type_ == 'd':
        if not is_dir:
            return False
    elif type_ == 'f':
        if not os.path.isfile(path):
            lprint(' - NOT FILE', verbose=verbose)
            return False
    elif type_ == 'l':
        if not os.path.islink(path):
            return False
    elif type_:
        raise ValueError(type_)

    # Apply other filters
    _path = Path(path)
    if extn and not _path.extn == extn:
        lprint(' - BAD EXTN', verbose=verbose)
        _result = False
    elif base and not _path.filename.startswith(base):
        _result = False
    elif filter_ and not passes_filter(path, filter_):
        lprint(' - FILTERED', verbose=verbose)
        _result = False
    elif name and not _path.filename == name:
        lprint(' - NAME FILTER', verbose=verbose)
        _result = False
    else:
        _result = True

    return _result


def get_copy_path_fn(path):
    """Get function to copy the given path.

    If the shift modifier is held, the path is converted to windows
    format (with backslash characters).

    Args:
        path (str): path to copy
    """

    def _copy_path_fn():
        from psyhive import qt
        _mods = qt.get_application().keyboardModifiers()
        _shift = _mods == qt.QtCore.Qt.ShiftModifier
        _path = abs_path(path, win=_shift)
        copy_text(_path)

    return _copy_path_fn


def get_owner(path):
    """Get owner of the given path.

    Args:
        path (str): path to check

    Returns:
        (str): path owner
    """

    def _get_file_security(filename, request):
        length = wintypes.DWORD()
        _get_file_security_w(filename, request, None, 0, ctypes.byref(length))
        if length.value:
            _sd = (wintypes.BYTE * length.value)()
            if _get_file_security_w(
                    filename, request, _sd, length, ctypes.byref(length)):
                return _sd
        return None

    def _get_security_descriptor_owner(sd_):
        if sd_ is not None:
            sid = _psid()
            sid_defaulted = wintypes.BOOL()
            if _get_security_desc_owner(
                    sd_, ctypes.byref(sid), ctypes.byref(sid_defaulted)):
                return sid
        return None

    def _look_up_account_sid(sid):
        if sid is not None:
            size = 256
            name = ctypes.create_unicode_buffer(size)
            domain = ctypes.create_unicode_buffer(size)
            cch_name = wintypes.DWORD(size)
            cch_domain = wintypes.DWORD(size)
            sid_type = wintypes.DWORD()
            if _lookup_accounts_sid(
                    None, sid, name, ctypes.byref(cch_name), domain,
                    ctypes.byref(cch_domain), ctypes.byref(sid_type)):
                return name.value, domain.value, sid_type.value
        return None, None, None

    _descriptor = ctypes.POINTER(wintypes.BYTE)
    _psid = ctypes.POINTER(wintypes.BYTE)
    _lpd_word = ctypes.POINTER(wintypes.DWORD)
    _lpd_bool = ctypes.POINTER(wintypes.BOOL)

    _owner_security_info = 0X00000001
    _sid_types = dict(enumerate(
        "User Group Domain Alias WellKnownGroup DeletedAccount "
        "Invalid Unknown Computer Label".split(), 1))

    _advapi32 = ctypes.windll.advapi32

    # MSDN windows/desktop/aa446639
    _get_file_security_w = _advapi32.GetFileSecurityW
    _get_file_security_w.restype = wintypes.BOOL
    _get_file_security_w.argtypes = [
        wintypes.LPCWSTR,  # File Name (in)
        wintypes.DWORD,  # Requested Information (in)
        _descriptor,  # Security Descriptor (out_opt)
        wintypes.DWORD,  # Length (in)
        _lpd_word, ]  # Length Needed (out)

    # MSDN windows/desktop/aa446651
    _get_security_desc_owner = _advapi32.GetSecurityDescriptorOwner
    _get_security_desc_owner.restype = wintypes.BOOL
    _get_security_desc_owner.argtypes = [
        _descriptor,  # Security Descriptor (in)
        ctypes.POINTER(_psid),  # Owner (out)
        _lpd_bool, ]  # Owner Exists (out)

    # MSDN windows/desktop/aa379166
    _lookup_accounts_sid = _advapi32.LookupAccountSidW
    _lookup_accounts_sid.restype = wintypes.BOOL
    _lookup_accounts_sid.argtypes = [
        wintypes.LPCWSTR,  # System Name (in)
        _psid,  # SID (in)
        wintypes.LPCWSTR,  # Name (out)
        _lpd_word,  # Name Size (inout)
        wintypes.LPCWSTR,  # Domain(out_opt)
        _lpd_word,  # Domain Size (inout)
        _lpd_word, ]  # SID Type (out)

    _request = _owner_security_info

    _path = os.path.abspath(path)
    _sd = _get_file_security(_path, _request)
    _sid = _get_security_descriptor_owner(_sd)
    _name, _, _ = _look_up_account_sid(_sid)

    return _name


def launch_browser(dir_):
    """Launch browser set to this dir.

    Args:
        dir_ (str): dir to open browser in
    """
    Dir(dir_).launch_browser()


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

    Returns:
        (bool): whether search completed successfully - ie. if an instance
            was found and the code was edited then false is returned
    """
    from psyhive import qt

    _found_instance = False
    for _file in qt.ProgressBar(
            files, 'Searching {:d} file{}', col='Aquamarine', show=not edit):

        dprint('CHECKING FILE', _file, verbose=verbose)

        _printed_path = False
        for _idx, _line in enumerate(read_file(_file).split('\n')):

            try:
                _text_in_line = text and text in _line
            except UnicodeDecodeError:
                continue

            # Check if this line should be printed
            _print_line = False
            if _text_in_line:
                lprint(' - MATCHED TEXT IN LINE', text, verbose=verbose)
                _print_line = True
            elif filter_ and passes_filter(
                    _line, filter_, case_sensitive=True):
                lprint(' - MATCHED FILTER IN LINE', filter_, verbose=verbose)
                _print_line = True

            if _print_line:
                if not _printed_path:
                    lprint(abs_path(_file, win=win))
                lprint('{:>6} {}'.format('[{:d}]'.format(_idx+1), _line))
                _printed_path = True
                _found_instance = True
                if edit:
                    File(_file).edit(line_n=_idx+1)
                    return False

        if _printed_path:
            lprint()

    if not _found_instance:
        dprint('No instances found')

    return True


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
    else:
        _time = time.time()
        os.utime(file_, (_time, _time))


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

    test_path(os.path.dirname(file_))
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
