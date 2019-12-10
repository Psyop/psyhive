"""Utilities for managing tank."""

import os
import sys
import time

import tank
import sgtk

from psyhive import qt, icons, refresh
from psyhive.utils import lprint, store_result, get_single, dprint, abs_path


def find_tank_app(name, catch=True):
    """Find tank app for the given name.

    Args:
        name (str): app name
        catch (bool): offer to restart tank if app is missing

    Returns:
        (SgtkApp): tank app
    """
    _engine = tank.platform.current_engine()

    # Try exact match
    if name in _engine.apps:
        return _engine.apps[name]

    # Try suffix match
    _suffix_match = get_single([
        _key for _key in _engine.apps.keys()
        if _key.split('-')[-1] == name], catch=True)
    if _suffix_match:
        return _engine.apps[_suffix_match]

    if catch:
        qt.ok_cancel('Could not find tank app "{}".\n\nWould you like to '
                     'restart tank?'.format(name),
                     icon=icons.EMOJI.find('Kaaba'))
        restart_tank()
        return find_tank_app(name)

    raise RuntimeError('Could not find tank app '+name)


def find_tank_mod(name, app=None, catch=False):
    """Find a tank mod in sys.modules dict.

    Args:
        name (str): mod name search
        app (str): filename search
        catch (bool): no error on unable to find mod
    """
    _mods = [
        _mod for _mod in refresh.find_mods(filter_=name, file_filter=app)
        if _mod.__name__.endswith(name)]
    if not _mods:
        if catch:
            return None
        raise ValueError("Failed to find module "+name)
    return _mods[0]


@store_result
def get_current_engine():
    """Get current tank engine.

    If no engine exists, a default tk-shell engine is created.

    Returns:
        (SgtkEngine): tank engine
    """
    _current = tank.platform.current_engine()
    if _current:
        return _current

    # Create shell engine
    _project_path = os.getenv('PSYOP_PROJECT_PATH')
    _tk = sgtk.Sgtk(_project_path)
    _ctx = _tk.context_from_path(_project_path)
    _shell = tank.platform.start_engine('tk-shell', _tk, _ctx)
    return _shell


def reference_publish(file_, verbose=0):
    """Reference a publish into the current scene.

    Args:
        file_ (str): path to reference
        verbose (int): print process data
    """
    from psyhive import tk

    # Find ref util module
    _mgr = tk.find_tank_app('assetmanager')
    _ref_util = tk.find_tank_mod(
        'tk_multi_assetmanager.reference_util', catch=True)
    if not _ref_util:
        _mgr.init_app()
        _ref_util = tk.find_tank_mod(
            'tk_multi_assetmanager.reference_util')
    lprint('REF UTIL', _ref_util, verbose=verbose)

    _ref_list = _mgr.reference_list
    _pub_dir = _ref_list.asset_manager.publish_directory
    _publish = _pub_dir.publish_from_path(file_)
    lprint('PUBLISH', _publish, verbose=verbose)

    _ref = _ref_util.reference_publish(_publish)
    lprint('REF', _ref, verbose=verbose)

    return _ref[0]


def restart_tank(force=True, verbose=0):
    """Restart shotgun toolkit (and remove unused modules).

    Args:
        force (bool): remove leftover libs with no confirmation
        verbose (int): print process data
    """
    _start = time.time()
    sgtk.platform.restart()
    _clean_leftover_modules(force=force, verbose=verbose)
    dprint("RESTARTED TANK ({:.02f}s)".format(time.time() - _start))


def _clean_leftover_modules(force=False, verbose=0):
    """Clean unused tk modules from sys.modules dict.

    Args:
        force (bool): remove leftover libs with no confirmation
        verbose (int): print process data
    """
    _engine = tank.platform.current_engine()

    # Find leftover modules
    _to_delete = []
    for _app_name in _engine.apps:
        _app = _engine.apps[_app_name]
        _id = _app._TankBundle__module_uid
        if not _id:
            continue
        lprint(_app_name, verbose=verbose)
        lprint(_id, verbose=verbose > 1)

        for _mod in refresh.find_mods():
            if _app_name not in _mod.__file__:
                continue
            if not _mod.__name__.startswith('tkimp'):
                continue
            if not _mod.__name__.startswith(_id):
                lprint(' - DELETE', _mod, verbose=verbose > 1)
                _to_delete.append(_mod.__name__)
                continue
            lprint(
                ' - {:80} {}'.format(_mod.__name__, abs_path(_mod.__file__)),
                verbose=verbose)
        lprint(verbose=verbose)

    # Remove modules
    if _to_delete:
        if not force:
            qt.ok_cancel(
                'Delete {:d} leftover modules?'.format(len(_to_delete)))
        for _mod_name in _to_delete:
            del sys.modules[_mod_name]
    else:
        print 'Nothing to clean'
