"""Utilities for managing tank."""

import os
import pprint
import sys
import time

import tank

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


def find_tank_mod(name, app=None, catch=False, safe=False, verbose=0):
    """Find a tank mod in sys.modules dict.

    Args:
        name (str): mod name search
        app (str): filename search
        catch (bool): no error on unable to find mod
        safe (bool): error if there is more than one matching module
        verbose (int): print process data

    Returns:
        (mod): matching tank module
    """
    _mods = [
        _mod for _mod in refresh.find_mods(filter_=name, file_filter=app)
        if _mod.__name__.endswith(name)]
    if verbose:
        pprint.pprint(_mods)
    if not _mods:
        if catch:
            return None
        raise ValueError("Failed to find module "+name)
    _mod = get_single(_mods) if safe else _mods[0]
    return _mod


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
    _tk = tank.Sgtk(_project_path)
    _ctx = _tk.context_from_path(_project_path)
    _shell = tank.platform.start_engine('tk-shell', _tk, _ctx)
    return _shell


def reference_publish(file_, verbose=0):
    """Reference a publish into the current scene.

    Args:
        file_ (str): path to reference
        verbose (int): print process data
    """
    from psyhive import tk2

    # Find ref util module
    _mgr = tk2.find_tank_app('assetmanager')
    _ref_util = tk2.find_tank_mod(
        'tk_multi_assetmanager.reference_util', catch=True)
    if not _ref_util:
        _mgr.init_app()
        _ref_util = tk2.find_tank_mod(
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

    tank.platform.restart()

    # Make sure asset manager mods loaded
    _ass_mgr = find_tank_app('assetmanager')
    _ass_mgr.init_app()
    _ass_mgr.publish_directory.publish_from_path('asdadasd')

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
        _other_name = _get_app_other_name(_app_name)
        _app = _engine.apps[_app_name]
        _id = _app._TankBundle__module_uid
        if not _id:
            lprint('MISSING ID', _app_name, verbose=verbose > 1)
            continue
        lprint(_app_name, verbose=verbose)
        lprint(' -', _other_name, verbose=verbose > 1)
        lprint(' -', _id, verbose=verbose > 1)

        for _mod in refresh.find_mods():
            if (
                    _app_name not in _mod.__file__ and
                    _other_name not in _mod.__file__):
                continue
            if not _mod.__name__.startswith('tkimp'):
                continue
            if not _mod.__name__.startswith(_id):
                lprint(' - DELETE', _mod, verbose=verbose > 1)
                _to_delete.append(_mod.__name__)
                continue
            _name = '.'.join(_mod.__name__.split('.')[1:])
            lprint(
                ' - {:90} {}'.format(_name, abs_path(_mod.__file__)),
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


def _get_app_other_name(name):
    """Get other name of a tank app.

    Tank apps seems to have psy/tk prefixes interchangeably so this allows
    the both names to be tested for.

    eg. tk-multi-cache -> psy-multi-cache
        psy-multi-assetmanager -> tk-multi-assetmanager

    Args:
        name (str): app name to convert

    Returns:
        (str): other name
    """
    _tokens = name.split('-')
    if _tokens[0] == 'psy':
        return '-'.join(['tk']+_tokens[1:])
    elif _tokens[0] == 'tk':
        return '-'.join(['psy']+_tokens[1:])
    raise ValueError(name)
