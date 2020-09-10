"""Tools for managing yeti caching."""

from maya import cmds

from psyhive import tk2, qt
from psyhive.utils import get_single, lprint

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_parent, set_namespace, load_plugin


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
        _cache_ns = cache.output_name
        _ref = ref_ or ref.find_ref(_cache_ns)
        print ' - REF', _ref
        assert cache.channel.startswith(_cache_ns+'_')
        _node_name = cache.channel[len(_cache_ns+'_'):]
        _yeti = _ref.get_node(_node_name, catch=True)
        if not _yeti:
            _top_node = _ref.find_top_node()
            set_namespace(':'+_ref.namespace)
            _yeti = hom.CMDS.createNode('pgYetiMaya', name=_node_name)
            set_namespace(':')
            cmds.parent(get_parent(_yeti), _top_node)
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
        caches (TTOutputFileSeqBase list): caches to apply
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
        caches (TTOutputFileSeqBase list): caches to apply
    """
    for _cache in caches:

        # Get node name
        _cache_ns = _cache.output_name
        assert _cache.channel.startswith(_cache_ns+'_')
        _node_name = _cache.channel[len(_cache_ns+'_'):]
        print 'NODE NAME', _node_name

        # Get yeti node
        load_plugin('pgYetiMaya')
        if cmds.objExists(_node_name):
            _yeti = hom.HFnDependencyNode(_node_name)
        else:
            _yeti = hom.CMDS.createNode('pgYetiMaya', name=_node_name)
        print 'YETI', _yeti

        apply_cache(_cache, yeti=_yeti)


def find_yeti_caches(root, verbose=0):
    """Find yeti caches in the given root.

    This finds all output names which are yeti caches in all steps in
    the given asset/shot root.

    Args:
        root (TTRootBase): root to search
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
