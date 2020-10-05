"""Tools for managing yeti caching."""

from maya import cmds

from psyhive import tk2, qt
from psyhive.utils import get_single, lprint, get_plural

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import set_namespace, load_plugin

from . import yeti_write


def apply_cache(cache, yeti=None, ref_=None):
    """Apply a yeti cache.

    Args:
        cache (Seq): cache to apply
        yeti (HFnDependencyNode): for node to apply to
        ref_ (FileRef): reference to apply cache to
    """
    print 'APPLYING CACHE', cache

    # Get yeti node, creating if needed
    if yeti:
        _yeti = yeti
    else:
        assert cache.output_name.count('Yeti_') == 1
        _cache_ns, _tfm_name = cache.output_name.split('Yeti_')
        _yeti_name = _tfm_name+'Shape'
        _ref = ref_ or ref.find_ref(_cache_ns)
        print ' - REF', _ref
        _yeti = _ref.get_node(_yeti_name, catch=True)
        if not _yeti:
            _top_node = _ref.find_top_node()
            set_namespace(':'+_ref.namespace)
            _yeti = hom.CMDS.createNode('pgYetiMaya', name=_yeti_name)
            if not _yeti.get_parent() == _ref.get_node(_tfm_name):
                _yeti.get_parent().rename(_tfm_name)
            set_namespace(':')
            cmds.parent(_yeti.get_parent(), _top_node)
    print ' - YETI', _yeti

    # Apply cache
    _yeti.plug('cacheFileName').set_val(cache.path)
    _yeti.plug('fileMode').set_val(1)
    _yeti.plug('overrideCacheWithInputs').set_val(False)


def apply_caches_to_sel_asset(caches):
    """Apply yeti caches to the selected asset.

    The asset can be selected by selecting any node in the reference.

    If the asset doesn't have a matching yeti node, it will be created.

    Args:
        caches (TTOutputFileSeq list): caches to apply
    """
    print 'APPLY CACHES', caches

    # Get asset
    _ref = ref.get_selected(catch=True)
    if not _ref:
        qt.notify_warning(
            "No asset selected.\n\nPlease select the asset you apply the "
            "cache to.")
        return
    print 'REF', _ref

    # Apply caches to yeti nodes
    for _cache in caches:
        apply_cache(_cache, ref_=_ref)


def apply_caches_in_root_namespace(caches):
    """Apply yeti caches in the root namespace.

    Yeti nodes which don't currently exist will be created with no namespace.

    Args:
        caches (TTOutputFileSeq list): caches to apply
    """
    for _cache in caches:

        print 'READ CACHE', _cache

        assert _cache.output_name.count('Yeti_') == 1
        _, _tfm_name = _cache.output_name.split('Yeti_')
        _yeti_name = _tfm_name+'Shape'
        print ' - NODE NAME', _tfm_name, _yeti_name

        # Get yeti node
        load_plugin('pgYetiMaya')
        if cmds.objExists(_yeti_name):
            _yeti = hom.HFnDependencyNode(_yeti_name)
        else:
            _yeti = hom.CMDS.createNode('pgYetiMaya', name=_yeti_name)
            print ' - CREATED YETI', _yeti
            if not _yeti.get_parent() == _tfm_name:
                cmds.rename(_yeti.get_parent(), _tfm_name)
                print ' - RENAMED PARENT', _yeti.get_parent()

        print ' - YETI', _yeti

        apply_cache(_cache, yeti=_yeti)


def find_yeti_caches(root, verbose=0):
    """Find yeti caches in the given root.

    This finds all output names which are yeti caches in all steps in
    the given asset/shot root.

    Args:
        root (TTRoot): root to search
        verbose (int): print process data

    Returns:
        (TTOutputNameBase list): caches
    """
    tk2.clear_caches()
    _root = tk2.obtain_cacheable(root)

    # Find fxcache names
    _steps = _root.find_step_roots()
    _fx_caches = []
    for _step in _steps:
        lprint('CHECKING STEP', _step, verbose=verbose)
        _fx_caches += [
            _name for _name in _step.find_output_names(output_type='fxcache')
            if 'Yeti' in _name.output_name]
    lprint('FOUND {:d} FX CACHES'.format(len(_fx_caches)), verbose=verbose)

    # Find vers with yeti caches
    _yeti_vers = []
    for _fx_cache in _fx_caches:
        _vers = _fx_cache.find_versions()
        if not _vers:
            continue
        for _ver in _vers:
            _out = get_single(_ver.find_files(format_='yeti'), catch=True)
            if _out:
                _yeti_vers.append(_ver)

    return _yeti_vers


def update_all(parent):
    """Update all yeti nodes to use latest cache.

    Args:
        parent (QDialog): parent dialog
    """
    print 'UPDATE ALL YETIS'

    # Check yetis to update
    _to_update = []
    for _yeti in hom.find_nodes(type_='pgYetiMaya'):

        print _yeti
        _file = _yeti.plug('cacheFileName').get_val()
        if _file:
            print ' - CUR', _file
        _latest = yeti_write.yeti_to_output(_yeti).find_latest()
        if not _latest:
            print ' - NO CACHES FOUND'
            continue

        print ' - LATEST', _latest.path
        if _file != _latest:
            print ' - NEEDS UPDATE'
            _to_update.append((_yeti, _latest))

    # Confirm
    print '{:d} CACHE{} NEED UPDATE'.format(
        len(_to_update), get_plural(_to_update).upper())
    if not _to_update:
        qt.notify('All caches are up to date', title='Update caches',
                  parent=parent)
        return
    qt.ok_cancel(
        'Update {:d} cache{}?'.format(
            len(_to_update), get_plural(_to_update)),
        title='Update caches', parent=parent)

    # Update
    for _yeti, _latest in qt.progress_bar(
            _to_update, 'Updating {:d} cache{}'):
        print _yeti, _latest
        apply_cache(yeti=_yeti, cache=_latest)
