"""Tools recaching a work file."""

import collections
import sys

import maya
from maya import cmds

import tank

from psyhive import qt, tk
from psyhive.utils import dprint, get_plural, lprint, check_heart
from maya_psyhive import ref


def _exec_recache(namespaces, confirm, new_scene, farm):
    """Execute a recache on the current workfile.

    Args:
        namespaces (str list): list of namespaces to recache
        confirm (bool): confirm before execute
        new_scene (bool): new scene after recache
        farm (bool): submit recache to farm
    """

    class _FakeResolver(object):

        def __init__(self, all_items, conflicts, version):
            self.user_data = all_items, version
            self.conflicts = conflicts

    class _FakeConflict(object):

        def __init__(self, namespace, cache):
            _user_data = collections.namedtuple('UserData', ['id'])
            self.user_data = _user_data(id=namespace)
            self.resolution = None if cache else _skip

    _engine = tank.platform.current_engine()
    _cache = _engine.apps['psy-multi-cache']
    check_heart()

    # Use resolver to limit items to cache
    _cache.init_app()
    _mod = sys.modules[_cache.cache_controller.__module__]
    _skip = _mod.PublishConflictResolution.SKIP
    _model = _cache.cache_controller.model
    _all_items = [
        _item.item_data
        for _item in _model.cache_list.selected_items]
    _conflicts = [
        _FakeConflict(namespace=_item.id, cache=_item.id in namespaces)
        for _item in _all_items]
    _resolver = _FakeResolver(
        all_items=_all_items, conflicts=_conflicts, version=_model.version)

    # Version up and cache
    if confirm:
        qt.ok_cancel('Submit re-cache to farm?')

    if farm:
        _cache.cache_controller.model.cache_on_farm(resolver=_resolver)
    else:
        _cache.cache_controller.model.cache(resolver=_resolver)

    dprint('SUBMITTED {:d}/{:d} REFS'.format(len(namespaces), len(_all_items)))
    if new_scene:
        cmds.file(new=True, force=True)


def _recache_work_file(
        work_file, namespaces, confirm=False, new_scene=False, farm=True,
        parent=None):
    """Recache the given work file.

    The work file is opened, versioned up and the recached.


    Args:
        work_file (TTWorkFileBase): work file to recache
        namespaces (str list): list of assets to recache
        confirm (bool): confirm before execute
        new_scene (bool): new scene after recache
        farm (bool): submit recache to farm
        parent (QDialog): parent interface (for dialog positioning)
    """
    dprint('RECACHING', work_file.path)

    _engine = tank.platform.current_engine()
    _fileops = _engine.apps['psy-multi-fileops']

    # Load the scene
    work_file.load()
    maya.utils.processIdleEvents()
    _fileops.init_app()

    # Update assets
    _updated = []
    for _ns in qt.ProgressBar(
            namespaces, 'Updating {:d} asset{}', col='LightSteelBlue',
            parent=parent):
        _ref = ref.find_ref(_ns)
        if not _ref.is_loaded():
            _ref.load()
        _cur_asset = tk.TTAssetOutputFile(_ref.path)
        _latest_asset = _cur_asset.get_latest()
        lprint(' - UPDATING {} v{:03d} -> v{:03d}'.format(
            _ref.namespace, _cur_asset.version, _latest_asset.version))
        if _cur_asset.is_latest():
            lprint('   - NO UPDATE REQUIRED')
            continue
        _ref.swap_to(_latest_asset.path)
        _updated.append(_ref.namespace)

    # Version up
    _fileops.init_app()
    maya.utils.processIdleEvents()
    _engine = tank.platform.current_engine()
    _fileops = _engine.apps['psy-multi-fileops']
    _fileops.version_up_workfile()
    maya.utils.processIdleEvents()
    tk.cur_work().set_comment('Versioned up by recacher tool')

    _exec_recache(
        namespaces=namespaces, new_scene=new_scene, confirm=confirm,
        farm=farm)


def recache_work_files(data, farm=True, parent=None):
    """Recache the given list of work files.

    Args:
        data (list): work files and namespaces to recache
        farm (bool): submit recaches to farm
        parent (QDialog): parent interface (for dialog positioning)
    """
    _pos = parent.get_c() if parent else None
    qt.ok_cancel(
        'Re-cache {:d} work file{}?'.format(len(data), get_plural(data)),
        pos=_pos)

    for _work_file, _namespaces in qt.ProgressBar(
            data, "Re-caching {:d} work file{}", col="DeepSkyBlue", pos=_pos,
            parent=parent):
        print 'RECACHE', _work_file.path
        print _namespaces
        print
        _recache_work_file(
            work_file=_work_file, namespaces=sorted(_namespaces),
            farm=farm, parent=parent)

    # Completed notification
    if farm:
        _msg = 'Submitted {:d} work file{} to farm'
    else:
        _msg = 'Cached {:d} work file{} locally'
    qt.notify(_msg.format(len(data), get_plural(data)), pos=_pos)
