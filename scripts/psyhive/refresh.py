"""Tools for refresh code within a python session."""

import sys
import time

from psyhive import qt
from psyhive.tools.err_catcher import Traceback
from psyhive.utils import (
    abs_path, lprint, passes_filter, apply_filter, dprint)

CODE_ROOT = 'P:/global/code/pipeline/bootstrap'

_RELOAD_ORDER = [
    'psyhive.utils.misc',
    'psyhive.utils.cache',
    'psyhive.utils.path',
    'psyhive.utils.py_file.docs',
    'psyhive.utils.py_file.base',
    'psyhive.utils.py_file.arg',
    'psyhive.utils.py_file.def_',
    'psyhive.utils.py_file.class_',
    'psyhive.utils.py_file',
    'psyhive.utils',
    'psyhive.icons.set_',
    'psyhive.icons',
    'psyhive.qt.wrapper.mgr',
    'psyhive.qt.wrapper.widgets',
    'psyhive.qt.wrapper',
    'psyhive.qt.misc',
    'psyhive.qt.interface',
    'psyhive.qt',
    'psyhive.py_gui',
    'psyhive.pipe.project',
    'psyhive.pipe.shot',
    'psyhive.pipe',
    'psyhive.tools',
    'psyhive',
    'maya_psyhive.utils',
    'maya_psyhive.open_maya',
    'maya_psyhive.tools.batch_cache.tmpl_cache',
    'maya_psyhive.tools.batch_cache.disk_handler',
    'maya_psyhive.tools.batch_cache.sg_handler',
    'maya_psyhive.tools.batch_cache',
    'maya_psyhive.tools',
    'maya_psyhive.startup',
    'maya_psyhive',
    'hv_test.diary.entry',
    'hv_test.diary',
    'hv_test.tools',
    'hv_test',
]


def add_sys_path(path):
    """Add a path to sys.path list.

    Any existing instances are removed and then the path is inserted
    at the front of sys.path.

    Args:
        path (str): path to add
    """
    _path = abs_path(path)
    while _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)


def find_mods(filter_=None, file_filter=None):
    """Find modules in sys.modules dict.

    Any modules without names or files are ignored.

    Args:
        filter_ (str): module name filter
        file_filter (str): module file path filter
    """
    _mods = []
    for _mod_name in sorted(sys.modules.keys()):
        if not passes_filter(_mod_name, filter_):
            continue
        _mod = sys.modules[_mod_name]
        if not _mod:
            continue
        _file = getattr(_mod, '__file__', None)
        if not _file:
            continue
        _file = abs_path(_file)
        if not passes_filter(_file, file_filter):
            continue
        _mods.append(_mod)
    return _mods


def get_mod_sort(order):
    """Get sort for modules based on the given order.

    Args:
        order (str list): ordering for modules
    """

    def _mod_sort(name):

        # Apply default sort
        _val = 10.0
        if 'utils' in name:
            _val -= 0.03
        if 'base' in name:
            _val -= 0.02
        if 'misc' in name:
            _val -= 0.01
        if 'tools' in name:
            _val += 0.01
        if 'tests' in name:
            _val += 0.03
        _val -= name.count('.')*0.1

        # Apply ordering
        _idx = 0
        for _idx, _name in enumerate(order):
            if name.startswith(_name) or name == _name:
                break
        _val += _idx*10

        return _val

    return _mod_sort


def reload_libs(
        mod_names=None, sort=None, execute=True, filter_=None,
        close_interfaces=True, catch=False, check_root=None,
        verbose=1):
    """Reload libraries.

    Args:
        mod_names (str list): override list of modules to reload
        sort (fn): module reload sort function
        execute (bool): execute the reload (otherwise just print
            the sorted list)
        filter_ (str): filter the list of modules
        close_interfaces (bool): close interfaces before refresh
        catch (bool): no error on fail to reload
        check_root (str): compare module locations to this root - this
            is used to check if a location has been successfully changed
        verbose (int): print process data

    Returns:
        (bool): whether all module were successfully reloaded and
            their paths updated the root (if applicable)
    """
    if close_interfaces:
        qt.close_all_interfaces()

    # Get list of mod names to sort
    if not mod_names:
        _mod_names = apply_filter(sys.modules.keys(), 'hv_test psyhive')
    else:
        _mod_names = mod_names
    _sort = sort or get_mod_sort(order=_RELOAD_ORDER)
    if filter_:
        _mod_names = apply_filter(_mod_names, filter_)
    _mod_names.sort(key=_sort)

    # Reload the modules
    _count = 0
    _start = time.time()
    _fails = 0
    for _mod_name in _mod_names:

        _mod = sys.modules[_mod_name]
        if not _mod:
            continue

        # Try to reload
        if execute:
            _start = time.time()
            try:
                reload(_mod)
            except ImportError as _exc:
                Traceback().pprint()
                if not catch:
                    qt.ok_cancel(
                        'Failed to reload "{}".\n\nRemove from '
                        'sys.path?'.format(_mod_name),
                        verbose=0)
                    del sys.modules[_mod_name]
                continue
            _dur = time.time() - _start

        _count += 1
        _file = _mod.__file__
        _name = _mod_name
        if len(_name) > 43:
            _name = _name[:40]+' ...'
        lprint(
            '{:<7.02f} {:<45} {:5.02f}s    {}'.format(
                _sort(_mod_name), _name, _dur, abs_path(_file)),
            verbose=verbose > 1)

        if check_root and not abs_path(_file).startswith(check_root):
            _fails += 1

    # Print summary
    _msg = 'Reloaded {:d} libs in {:.02f}s'.format(
        _count, time.time()-_start)
    if check_root:
        _msg += ' ({:d} fails)'.format(_fails)
    dprint(_msg, verbose=verbose)

    return not _fails


def update_libs(check_root, mod_names=None, sort=None):
    """Update a list of modules to a new location.

    Args:
        check_root (str): location to check paths match to
        mod_names (str list): list of modules to update
        sort (fn): module sort function
    """
    for _idx in range(6):
        dprint('Updating modules - attempt', _idx+1)
        _result = reload_libs(
            catch=True, check_root=check_root, mod_names=mod_names,
            sort=sort)
        dprint('Updating modules:', 'success' if _result else 'failed')
        if _result:
            break
