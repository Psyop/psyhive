"""Tools for refresh code within a python session."""

import copy
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
    'psyhive.utils.path.p_utils',
    'psyhive.utils.path.p_path',
    'psyhive.utils.path.p_dir',
    'psyhive.utils.path.p_file',
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
    'psyhive.qt.wrapper.gui.painter',
    'psyhive.qt.wrapper.gui.pixmap',
    'psyhive.qt.wrapper.gui',
    'psyhive.qt.wrapper.widgets',
    'psyhive.qt.wrapper',
    'psyhive.qt.misc',
    'psyhive.qt.msg_box',
    'psyhive.qt.dialog.dg_base',
    'psyhive.qt.dialog.ui_dialog_3',
    'psyhive.qt.multi_select_',
    'psyhive.qt',
    'psyhive.py_gui',
    'psyhive.pipe.project',
    'psyhive.pipe.shot',
    'psyhive.pipe',
    'psyhive.tk2',
    'psyhive.tk2.tk_cache',
    'psyhive.tk.misc',
    'psyhive.tk.templates.tt_base',
    'psyhive.tk.templates.tt_base_output',
    'psyhive.tk.templates.tt_base_work',
    'psyhive.tk.templates',
    'psyhive.tk',
    'psyhive.tools',
    'psyhive',

    'maya_psyhive.utils',
    'maya_psyhive.open_maya.utils',
    'maya_psyhive.open_maya.base_array3',
    'maya_psyhive.open_maya.point',
    'maya_psyhive.open_maya.vector',
    'maya_psyhive.open_maya.bounding_box',
    'maya_psyhive.open_maya.plug',
    'maya_psyhive.open_maya.dag_path',
    'maya_psyhive.open_maya.base_node',
    'maya_psyhive.open_maya.base_transform',
    'maya_psyhive.open_maya.mesh',
    'maya_psyhive.open_maya.cpnt_mesh',
    'maya_psyhive.open_maya',
    'maya_psyhive.tools.batch_cache.tmpl_cache',
    'maya_psyhive.tools.batch_cache.disk_handler',
    'maya_psyhive.tools.batch_cache.sg_handler',
    'maya_psyhive.tools.batch_cache',
    'maya_psyhive.tools.batch_cache2.bc_tmpl_cache',
    'maya_psyhive.tools.batch_cache2.bc_disk_handler',
    'maya_psyhive.tools.batch_cache2.bc_sg_handler',
    'maya_psyhive.tools.batch_cache2.bc_interface',
    'maya_psyhive.tools.batch_cache2',
    'maya_psyhive.tools',
    'maya_psyhive.shows._fr_',
    'maya_psyhive.shows.frasier',
    'maya_psyhive.shows',
    'maya_psyhive.startup',
    'maya_psyhive',

    'hv_test.startup.hsu_buttons',
    'hv_test.startup',

    'hv_test.tools.colour_bro.pantone',
    'hv_test.tools.colour_bro',
    'hv_test.tools.qube.qb_subjob',
    'hv_test.tools.qube.qb_task',
    'hv_test.tools.qube.qb_job',
    'hv_test.tools.qube.qb_core',
    'hv_test.tools.qube.hive_qube',
    'hv_test.tools.qube',

    'hv_test.diary.y19.d0726._machi.player',
    'hv_test.diary.y19.d0726._machi.robot',
    'hv_test.diary.entry',
    'hv_test.diary',
    'hv_test.tools',
    'hv_test',
]


def add_sys_path(path, mode='prepend'):
    """Add a path to sys.path list.

    Any existing instances are removed and then the path is inserted
    at the front of sys.path.

    Args:
        path (str): path to add
        mode (str): how to add the path (append or prepend)
    """
    _path = abs_path(path)
    while _path in sys.path:
        sys.path.remove(_path)

    if mode == 'prepend':
        sys.path.insert(0, _path)
    elif mode == 'append':
        sys.path.append(_path)
    else:
        raise ValueError(mode)


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
            if name == _name:
                break
            if name.startswith(_name+'.') and name not in order:
                _val += 0.01
                break
            if name.startswith(_name) and name not in order:
                _val += 0.02
                break
        _val += _idx*10

        return _val

    return _mod_sort


def _reload_mod(mod, mod_name, execute, delete, catch, sort, verbose):
    """Reload the given module.

    Args:
        mod (module): module to reload
        mod_name (str): module name
        execute (bool): execute the reload
        delete (bool): delete and reimport module on reload
        catch (bool): no error on fail to reload
        sort (func): module reload sort function
        verbose (int): print process data
    """

    # Try to reload
    _dur = 0.0
    if execute:
        _start = time.time()
        try:
            reload(mod)
        except ImportError as _exc:
            Traceback().pprint()
            if not catch:
                qt.ok_cancel(
                    'Failed to reload "{}".\n\nRemove from '
                    'sys.path?'.format(mod_name),
                    verbose=0)
                del sys.modules[mod_name]
            return
        _dur = time.time() - _start

    # Apply delete once reload works
    if delete:
        del sys.modules[mod_name]
        __import__(mod_name, fromlist=mod_name.split('.'))

    # Print status
    if len(mod_name) > 53:
        mod_name = mod_name[:50]+' ...'
    lprint(
        '{:<7.02f} {:<55} {:5.02f}s    {}'.format(
            sort(mod_name), mod_name, _dur, abs_path(mod.__file__)),
        verbose=verbose > 1)


def reload_libs(
        mod_names=None, sort=None, execute=True, filter_=None,
        close_interfaces=True, catch=False, check_root=None,
        delete=False, verbose=1):
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
        delete (bool): delete and reimport modules on reload (to flush vars)
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

        _reload_mod(mod=_mod, mod_name=_mod_name, execute=execute, sort=_sort,
                    delete=delete, verbose=verbose, catch=catch)

        _count += 1
        if check_root and not abs_path(_mod.__file__).startswith(
                abs_path(check_root)):
            _fails += 1

    # Print summary
    _msg = 'Reloaded {:d} libs in {:.02f}s'.format(
        _count, time.time()-_start)
    if check_root:
        _msg += ' ({:d} fails)'.format(_fails)
    dprint(_msg, verbose=verbose)

    return not _fails


def remove_sys_path(path):
    """Remove a path from sys.path list.

    Paths are compared in their absolute form.

    Args:
        path (str): path to remove
    """
    _path = abs_path(path)
    for _sys_path in copy.copy(sys.path):
        if abs_path(_sys_path) == _path:
            print 'REMOVING', _sys_path
            sys.path.remove(_sys_path)


def update_libs(check_root, mod_names=None, sort=None, close_interfaces=True,
                verbose=1):
    """Update a list of modules to a new location.

    Args:
        check_root (str): location to check paths match to
        mod_names (str list): list of modules to update
        sort (fn): module sort function
        close_interfaces (bool): close interfaces before refresh
        verbose (int): print process data
    """
    for _idx in range(6):
        dprint('Updating modules - attempt', _idx+1)
        _result = reload_libs(
            catch=True, check_root=check_root, mod_names=mod_names,
            sort=sort, close_interfaces=close_interfaces, verbose=verbose)
        dprint('Updating modules:', 'success' if _result else 'failed')
        if _result:
            break
