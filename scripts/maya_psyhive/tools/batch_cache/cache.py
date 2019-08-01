"""Tools recaching a work file."""

import collections
import pprint
import sys

import maya
from maya import cmds

import tank

from psyhive import qt, tk
from psyhive.utils import dprint, get_plural, lprint, check_heart
from maya_psyhive import ref

from maya_psyhive.tools.batch_cache.tmpl_cache import CTTMayaShotWork


def _exec_cache(
        namespaces, confirm=True, new_scene=False, farm=True,
        verbose=1):
    """Execute a recache on the current workfile.

    Args:
        namespaces (str list): list of namespaces to recache
        confirm (bool): confirm before execute
        new_scene (bool): new scene after recache
        farm (bool): submit recache to farm
        verbose (int): print process data
    """

    class _FakeResolver(object):

        def __init__(self, all_items, conflicts, version):
            self.user_data = all_items, version
            self.conflicts = conflicts

    class _FakeConflict(object):

        def __init__(self, id_, cache):
            _user_data = collections.namedtuple('UserData', ['id'])
            self.id_ = id_
            self.user_data = _user_data(id=self.id_)
            self.resolution = None if cache else _skip

        def __repr__(self):
            return '<Conflict:{}>'.format(self.id_)

    _engine = tank.platform.current_engine()
    _cache_app = _engine.apps['psy-multi-cache']
    check_heart()

    # Use resolver to limit items to cache
    _cache_app.init_app()
    _mod = sys.modules[_cache_app.cache_controller.__module__]
    _skip = _mod.PublishConflictResolution.SKIP
    _model = _cache_app.cache_controller.model
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
    if confirm:
        qt.ok_cancel('Submit {:d} cache{} to farm?'.format(
            len(_to_cache), get_plural(_to_cache)))

    # Execute cache
    if farm:
        _cache_app.cache_controller.model.cache_on_farm(resolver=_resolver)
    else:
        _cache_app.cache_controller.model.cache(resolver=_resolver)
    dprint('{} {:d}/{:d} REFS'.format(
        'SUBMITTED' if farm else 'CACHED', len(namespaces), len(_all_items)))
    if new_scene:
        cmds.file(new=True, force=True)


def cache_work_file(
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
        _latest_asset = _cur_asset.find_latest()
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
    _cur_work = tk.cur_work(class_=CTTMayaShotWork)
    _cur_work.set_comment('Versioned up by batch cache tool')
    _cur_work.read_dependencies(new_scene=False)

    _exec_cache(
        namespaces=namespaces, new_scene=new_scene, confirm=confirm,
        farm=farm)
    cmds.file(new=True, force=True)


def cache_work_files(data, farm=True, parent=None):
    """Recache the given list of work files.

    Args:
        data (list): work files and namespaces to recache
        farm (bool): submit recaches to farm
        parent (QDialog): parent interface (for dialog positioning)
    """
    _pos = parent.get_c() if parent else None
    qt.ok_cancel(
        'Cache {:d} work file{}?'.format(len(data), get_plural(data)),
        pos=_pos, parent=parent, title='Confirm cache')

    for _work_file, _namespaces in qt.ProgressBar(
            data, "Caching {:d} work file{}", col="DeepSkyBlue", pos=_pos,
            parent=parent):
        print 'CACHE', _work_file.path
        print _namespaces
        print
        cache_work_file(
            work_file=_work_file, namespaces=sorted(_namespaces),
            farm=farm, parent=parent)

    # Completed notification
    if farm:
        _msg = 'Submitted {:d} work file{} to farm'
    else:
        _msg = 'Cached {:d} work file{} locally'
    qt.notify(
        _msg.format(len(data), get_plural(data)), pos=_pos,
        title='Complete', parent=parent)
