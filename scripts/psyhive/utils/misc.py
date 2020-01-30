"""Miscellaneous utility tools."""

import copy
import httplib
import functools
import os
import pprint
import random
import subprocess
import tempfile
import time
import types
import urllib2

import six


def bytes_to_str(bytes_):
    """Convert a number of bytes to a readable string.

    Args:
        bytes_ (int): byte count

    Returns:
        (str): bytes as a string
    """
    _size = float(bytes_)
    _labels = ["B", "K", "M", "G", "T", "P"]
    _factor = 0
    while _size > 1000:
        _factor += 1
        _size /= 1000
        if _factor > 5:
            raise RuntimeError("Could not convert: {:d}".format(bytes_))
    if _size == 0:
        return "0"
    _size = "{:.02f}".format(_size)
    return _size + _labels[_factor]


def chain_fns(*args):
    """Build a function that executes a list of functions in sequence.

    The list of functions provided are executed one after the other.

    Returns:
        (fn): chained function
    """

    def _get_chained_fn(args):

        # Catch args not funcs
        _fn_types = (types.FunctionType, types.MethodType,
                     types.BuiltinMethodType)
        for _arg in args:
            if not isinstance(_arg, _fn_types):
                raise TypeError('Arg is not function - {}'.format(_arg))

        def _chained_fn(*xargs):
            del xargs
            for _fn in args:
                _fn()
        return _chained_fn

    return _get_chained_fn(args)


def clamp(val, min_, max_):
    """Clamp the value in the given range.

    Args:
        val (float): value to clamp
        min_ (float): min value
        max_ (float): max value

    Returns:
        (float): clamped value
    """
    return min(max(val, min_), max_)


def copy_text(text, verbose=1):
    """Copy the given text to the clipboard.

    Args:
        text (str): text to copy
        verbose (int): print process data
    """
    from psyhive import qt

    _clip = qt.get_application().clipboard()
    _clip.setText(text)
    if '\n' in text:
        lprint("[copied]", verbose=verbose)
        lprint(text, verbose=verbose)
    else:
        lprint("[copied]", text, verbose=verbose)


def dev_mode():
    """Test whether dev mode env var is set."""
    return bool(os.environ.get('PSYOP_DEV'))


def dprint(*args, **kwargs):
    """Print text to terminal with a date prefix."""
    lprint(time.strftime('[%H:%M:%S]'), *args, **kwargs)


def get_cfg(namespace, verbose=0):
    """Read config from the given namespace.

    Args:
        namespace (str): namespace name to read from
        verbose (int): print process data

    Returns:
        (dict): config yaml file contents
    """
    from psyhive.utils.path import abs_path, read_yaml
    _yaml = abs_path(
        '../../../cfg/{}.yml'.format(namespace),
        root=os.path.dirname(__file__))
    lprint('YAML', _yaml, verbose=verbose)
    return read_yaml(_yaml)


def get_single(
        items, catch=False, name='item', verb='found', fail_message=None,
        error=None, verbose=0):
    """Get single item from a list.

    If the list does not contain exactly one item, the function will fail.

    Args:
        items (list): list of items
        catch (bool): on error return None rather than fail
        name (str): name of objects (for error message)
        verb (str): verb for object discovery (for error message)
        fail_message (str): override fail message
        error (Exception): override exception to raise on fail
        verbose (int): print process data

    Returns:
        (any): single list item
        (None): if there wasn't one item in the list and catch was used

    Raises:
        (ValueError): if the list did not contain exactly one item
    """
    _err_msg = None
    if not items:
        _err_msg = 'No {} {}'.format(name, verb)
    elif len(items) > 1:
        _err_msg = '{:d} {}{} {}'.format(
            len(items), name, get_plural(items), verb)

    # Handle fail
    if _err_msg:
        _err_msg = fail_message or _err_msg
        if catch:
            lprint(_err_msg, verbose=verbose > 1)
            return None
        if verbose:
            lprint('Found {:d} items:'.format(len(items)))
            pprint.pprint(items)
        _error = error or ValueError
        raise _error(_err_msg)

    if isinstance(items, set):
        items = list(items)

    return items[0]


def get_plural(items, plural='s'):
    """Get plural character for the given list of items.

    If the list has one item, this is an empty string. Otherwise, the
    's' character is returned.

    Args:
        items (list|int): list/number of items
        plural (str): override plural str (eg. for pass -> passes
            the plural str would be "es")

    Returns:
        (str): plural character(s)
    """
    if isinstance(items, (list, tuple, set, dict)):
        _count = len(items)
    elif isinstance(items, int):
        _count = items
    else:
        raise ValueError(items)
    return '' if _count == 1 else plural


def get_ord(idx):
    """Get ordinal for the given number.

    eg.

    1 -> 'st'
    2 -> 'nd'
    3 -> 'rd'
    4 -> 'th'

    Args:
        idx (int): number
    """
    _str = str(idx)
    if _str.endswith('1') and not _str.endswith('11'):
        return 'st'
    if _str.endswith('2') and not _str.endswith('12'):
        return 'nd'
    if _str.endswith('3') and not _str.endswith('13'):
        return 'rd'
    return 'th'


def get_time_t(val):
    """Get time tuple based on the given value.

    Args:
        val (float|stuct_time): value to convert

    Returns:
        (stuct_time): time tuple
    """
    if isinstance(val, float):
        return time.localtime(val)
    elif isinstance(val, time.struct_time):
        return val
    raise ValueError(val)


def last(items):
    """Mark the last item of a list.

    Returns a list of item pairs with the first item a boolean of whether
    this is the last item, and the second item the corresponding list
    item.

    eg. ['a', 'b', 'c'] -> [(False, 'a'), (False, 'b'), (True, 'c')]

    Args:
        items (list): list of items

    Returns:
        (tuple list): zipped list
    """
    _result = []

    _items = items
    if isinstance(_items, enumerate):
        _items = list(_items)

    _last = len(_items) - 1
    for _idx, _item in enumerate(_items):
        _result.append((_idx == _last, _item))

    return _result


def lprint(*args, **kwargs):
    """Print a list of strings to the terminal.

    This aims to replicate the py2 print statement but still be compatible
    with py3. The print can be supressed using verbose=0 kwarg.
    """
    if not kwargs.get('verbose', True):
        return
    print(' '.join([str(_arg) for _arg in args]))


def read_url(url, edit=False, attempts=5):
    """Read url contents.

    Args:
        url (str): url to read
        edit (bool): save html and open in editor
        attempts (int): number of attempts to download url

    Returns:
        (str): url response
    """
    from psyhive.utils import write_file, File, abs_path

    # Attempt to read data
    _data = None
    for _idx in range(attempts):
        try:
            _response = urllib2.urlopen(url)
            _data = _response.read()
        except (urllib2.HTTPError, httplib.IncompleteRead) as _exc:
            print 'FAILED({}) - {:d}'.format(type(_exc).__name__, _idx+1)
            time.sleep(2)
        else:
            break

    if not _data:
        raise RuntimeError('Failed to read '+url)

    if edit:
        _tmp_html = abs_path(tempfile.gettempdir()+'/tmp.html')
        write_file(file_=_tmp_html, text=_data, force=True)
        File(_tmp_html).edit()
        print 'Saved tmp html', _tmp_html

    return _data


def safe_zip(list_a, list_b):
    """Zip two lists together, erroring if they don't have the same length.

    Args:
        list_a (list): first list
        list_b (list): second list

    Returns:
        (list): zipped list
    """
    if not len(list_a) == len(list_b):
        print 'LIST A', list_a
        print 'LIST B', list_b
        raise ValueError(
            'Length of list a ({:d}) does not match length of list b '
            '({:d})'.format(len(list_a), len(list_b)))

    return [(_itema, _itemb) for _itema, _itemb in zip(list_a, list_b)]


def str_to_seed(string, offset=0):
    """Create a unique seeded random object based on a string.

    Args:
        string (str): string for seed
        offset (int): apply offset to seed

    Returns:
        (random.Random): seeded random object
    """
    _random = random.Random()
    if not isinstance(string, six.string_types):
        raise ValueError('Not string {} ({})'.format(string, type(string)))
    _total = offset
    for _idx, _chr in enumerate(string):
        _random.seed(ord(_chr)*(_idx+1))
        _total += int(_random.random()*100000)
    _random.seed(_total)
    return _random


def system(cmd, result=True, verbose=0):
    """Execute a system command.

    This supresses the windows shell window and pipes the reads the output.

    Args:
        cmd (str|list): commands to execute
        result (bool): wait for and return cmd result
        verbose (int): print process data

    Returns:
        (str): command output
    """
    if isinstance(cmd, list):
        _cmds = cmd
    else:
        _cmds = ["cmd", "/C"]+cmd.split()
    lprint(' '.join(_cmds), verbose=verbose)

    _si = subprocess.STARTUPINFO()
    _si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    _pipe = subprocess.Popen(
        _cmds,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=_si)

    if not result:
        return None
    return _pipe.communicate()[0]


def to_camel(text):
    """Convert text to camel case.

    Args:
        text (str): text to convert

    Returns:
        (str): camel text
    """
    return text.strip().lower().replace(' ', '_')


def to_nice(text):
    """Convert camel or snake case to a readable string.

    Args:
        text (str): text to convert

    Returns:
        (str): readable string
    """
    _text = text.strip('_')
    return _text[0].capitalize() + _text[1:].replace('_', ' ')


def val_map(val, in_min=0.0, in_max=1.0, out_min=0.0, out_max=1.0):
    """Map a float value from input range to output range.

    This mimics the java map function.

    Args:
        val (float): value
        in_min (float): input min
        in_max (float): input max
        out_min (float): output min
        out_max (float): output max

    Returns:
        (float): mapped value
    """
    _in_span = in_max-in_min
    _out_span = out_max-out_min
    _val_scaled = float(val-in_min)/float(_in_span)
    return out_min + (_val_scaled*_out_span)


def wrap_fn(func, *args, **kwargs):
    """Wrap the given function with the given args/kwargs.

    The result is a function which executes as if the original function
    had been executed with the given args/kwargs. This is similar to
    functools.partial except and args/kwargs passed to the new function
    are ignores (this allows the function to be used in maya ui callbacks).

    Args:
        func (fn): function to wrap
        arg_to_kwarg (str): map the first arg to a kwargs of the given name
        pass_data (bool): new function recieves args/kwargs on exec

    Returns:
        (fn): wrapped function
    """
    _pass_data = kwargs.get('pass_data')
    if _pass_data:
        kwargs.pop('pass_data')
    _arg_to_kwarg = kwargs.get('arg_to_kwarg')
    if _arg_to_kwarg:
        kwargs.pop('arg_to_kwarg')

    @functools.wraps(func)
    def _wrapped_fn(*xargs, **xkwargs):

        # Combine both args/kwargs
        if _pass_data:
            _args = list(args) + list(xargs)
            _kwargs = copy.copy(kwargs)
            for _key, _val in xkwargs.items():
                _kwargs[_key] = _val
            return func(*_args, **_kwargs)

        # Map an arg to kwarg
        if _arg_to_kwarg:
            _kwargs = kwargs
            _kwargs[_arg_to_kwarg] = xargs[0]
            return func(*args, **_kwargs)

        del xargs, xkwargs
        return func(*args, **kwargs)

    return _wrapped_fn
