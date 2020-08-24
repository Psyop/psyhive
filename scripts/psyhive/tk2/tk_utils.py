"""Utilities for managing tank."""

import collections
import os
import pprint
import sys
import time

import six
import tank

from psyhive import qt, icons, refresh, host
from psyhive.utils import (
    lprint, store_result, get_single, dprint, abs_path, get_path)


class _FakeResolver(object):
    """Used to communicate with cache tool."""

    def __init__(self, all_items, conflicts, version):
        """Constructor.

        Args:
            all_items (CacheItem list): all cache items
            conflicts (FakeConflict list): data on which items to cache
            version (int): model version
        """
        self.user_data = all_items, version
        self.conflicts = conflicts


class _FakeConflict(object):
    """Used to communicate with cache tool."""

    def __init__(self, id_, cache):
        """Constructor.

        Args:
            id_ (str): cache item namespace
            cache (bool): whether to cache item
        """
        _mod = find_tank_mod('psy_multi_cache.cache')
        _skip = _mod.PublishConflictResolution.SKIP
        _user_data = collections.namedtuple('UserData', ['id'])
        self.id_ = id_
        self.user_data = _user_data(id=self.id_)
        self.resolution = None if cache else _skip

    def __repr__(self):
        return '<Conflict:{}>'.format(self.id_)


def cache_scene(namespaces=None, farm=False, verbose=0):
    """Cache the current scene.

    Args:
        namespaces (str list): limit namespaces which are cached
        farm (bool): cache using farm
        verbose (int): print process data
    """
    _app = find_tank_app('cache')
    _app.init_app()

    if namespaces:

        # Use FakeResolver to limit items to cache
        _model = _app.cache_controller.model
        _all_items = [
            _item.item_data
            for _item in _model.cache_list.selected_items]
        lprint(
            ' - ALL ITEMS', len(_all_items), pprint.pformat(_all_items),
            verbose=verbose > 1)
        _conflicts = []
        for _item in _all_items:
            _cache = _item.id.replace(":renderCamShape", "") in namespaces
            _conflict = _FakeConflict(id_=_item.id, cache=_cache)
            _conflicts.append(_conflict)
        lprint(
            ' - CONFLICTS', len(_conflicts), pprint.pformat(_conflicts),
            verbose=verbose > 1)
        _resolver = _FakeResolver(
            all_items=_all_items, conflicts=_conflicts, version=_model.version)

        # Check cache
        _to_cache = [
            _conflict for _conflict in _conflicts if not _conflict.resolution]
        if not _to_cache:
            raise RuntimeError("Nothing found to cache")
        lprint(' - FOUND {:d} ITEMS TO CACHE'.format(len(_to_cache)))

    else:
        _resolver = None

    # Execute cache
    if farm:
        _app.cache_controller.model.cache_on_farm(resolver=_resolver)
    else:
        _app.cache_controller.model.cache(resolver=_resolver)


def capture_scene():
    """Capture current scene."""
    _app = find_tank_app('capture')
    _app.capture(view=False)


def find_tank_app(name, catch=True, verbose=0):
    """Find tank app for the given name.

    Args:
        name (str): app name
        catch (bool): offer to restart tank if app is missing
        verbose (int): print process data

    Returns:
        (SgtkApp): tank app
    """
    _engine = tank.platform.current_engine()

    if verbose:
        print 'TANK APPS:'
        pprint.pprint(_engine.apps.keys())

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


def publish_scene(comment, force=False):
    """Publish the current scene.

    Args:
        comment (str): publish comment
        force (bool): force save over without confirmation
    """
    from .. import tk2

    _publish = find_tank_app('publish')
    _fileops = find_tank_app('fileops')
    _ass_man = find_tank_app('assetmanager')

    _fileops.init_app()
    _publish.init_app()

    # Create publish type
    _mod = find_tank_mod(
        'tk_multi_publish.publish_types.scene.scene_publish')
    _type = _mod.ScenePublishType(app=_publish)

    # Create publish item
    _mod = find_tank_mod(
        'tk_multi_publish.publish_types.scene.scene_publish')
    _scn_pub = _mod.ScenePublish(app=_publish)

    # Create publish
    _mod = find_tank_mod('tk_multi_publish.publish')
    _pub = _mod.Publish(app=_publish, publish_type=_type)
    _pub._model._mode = 1
    _pub._model._publish_item = _scn_pub

    # Execute publish
    _start = time.time()
    host.save_scene(force=force)
    _pub._model.publish()
    _dur = time.time() - _start
    tk2.cur_work().set_comment(comment)
    print ' - PUBLISHED ASSET IN {:.02f}s'.format(_dur)

    # Update asset manager
    _start = time.time()
    _ass_man.init_app()
    _dur = time.time() - _start
    print ' - UPDATED ASSET MANAGER IN {:.02f}s'.format(_dur)


def reference_publish(file_, verbose=0):
    """Reference a publish into the current scene.

    Args:
        file_ (str): path to reference
        verbose (int): print process data
    """
    _file = get_path(file_)
    assert isinstance(_file, six.string_types)

    # Find ref util module
    _mgr = find_tank_app('assetmanager')
    _ref_util = find_tank_mod(
        'tk_multi_assetmanager.reference_util', catch=True)
    if not _ref_util:
        _init_tank()
        _ref_util = find_tank_mod('tk_multi_assetmanager.reference_util')
    lprint('REF UTIL', _ref_util, verbose=verbose)

    _ref_list = _mgr.reference_list
    _pub_dir = _ref_list.asset_manager.publish_directory
    _publish = _pub_dir.publish_from_path(_file)
    lprint('PUBLISH', _publish, verbose=verbose)
    if not _publish:
        raise RuntimeError('Failed to build publish '+_file)

    _ref = _ref_util.reference_publish(_publish)
    lprint('REF', _ref, verbose=verbose)
    _ref_list.update()

    return _ref[0]


def _init_tank():
    """Initiate tank for psyhive.

    This makes sure any modules used by psyhive are imported.
    """
    _ass_mgr = find_tank_app('assetmanager')
    _ass_mgr.init_app()
    _ass_mgr.publish_directory.publish_from_path('asdadasd')


def restart_tank(force=True, verbose=0):
    """Restart shotgun toolkit (and remove unused modules).

    Args:
        force (bool): remove leftover libs with no confirmation
        verbose (int): print process data
    """
    _start = time.time()

    tank.platform.restart()
    _init_tank()
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
