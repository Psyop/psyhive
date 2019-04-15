"""Miscellaneous utility tools."""

import functools
import os
import random
import subprocess
import time

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
        def _chained_fn():
            for _fn in args:
                _fn()
        return _chained_fn

    return _get_chained_fn(args)


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
        items, catch=False, name='items', verb='found', fail_message=None,
        verbose=0):
    """Get single item from a list.

    If the list does not contain exactly one item, the function will fail.

    Args:
        items (list): list of items
        catch (bool): on error return None rather than fail
        name (str): name of objects (for error message)
        verb (str): verb for object discovery (for error message)
        fail_message (str): override fail message
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
        _err_msg = '{:d} {} {}'.format(len(items), name, verbose)

    # Handle fail
    if _err_msg:
        _err_msg = fail_message or _err_msg
        if catch:
            lprint(_err_msg, verbose=verbose)
            return None
        raise ValueError(_err_msg)

    if isinstance(items, set):
        items = list(items)

    return items[0]


def get_plural(items):
    """Get plural character for the given list of items.

    If the list has one item, this is an empty string. Otherwise, the
    's' character is returned.

    Args:
        items (list): list of items to check

    Returns:
        (str): plural character
    """
    return '' if len(items) == 1 else ''


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

    _last = len(items) - 1
    for _idx, _item in enumerate(items):
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


def str_to_seed(string):
    """Create a unique seeded random object based on a string.

    Args:
        string (str): string for seed

    Returns:
        (random.Random): seeded random object
    """
    _random = random.Random()
    assert isinstance(string, six.string_types)
    _total = 0
    for _idx, _chr in enumerate(string):
        _random.seed(ord(_chr)*(_idx+1))
        _total += int(_random.random()*100000)
    _random.seed(_total)
    return _random


def system(cmd, verbose=0):
    """Execute a system command.

    This supresses the windows shell window and pipes the reads the output.

    Args:
        cmd (str|list): commands to execute
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

    return _pipe.communicate()[0]


def to_nice(text):
    """Convert camel or snake case to a readable string.

    Args:
        text (str): text to convert

    Returns:
        (str): readable string
    """
    _text = text.strip('_')
    return _text[0].capitalize() + _text[1:].replace('_', ' ')


def wrap_fn(func, *args, **kwargs):
    """Wrap the given function with the given args/kwargs.

    The result is a function which executes as if the original function
    had been executed with the given args/kwargs. This is similar to
    functools.partial except and args/kwargs passed to the new function
    are ignores (this allows the function to be used in maya ui callbacks).

    Args:
        func (fn): function to wrap

    Returns:
        (fn): wrapped function
    """

    _arg_to_kwarg = kwargs.get('arg_to_kwarg')
    if _arg_to_kwarg:
        kwargs.pop('arg_to_kwarg')

    @functools.wraps(func)
    def _wrapped_fn(*xargs, **xkwargs):

        # Map an arg to kwarg
        if _arg_to_kwarg:
            _kwargs = kwargs
            _kwargs[_arg_to_kwarg] = xargs[0]
            return func(*args, **_kwargs)

        del xargs, xkwargs
        return func(*args, **kwargs)

    return _wrapped_fn
