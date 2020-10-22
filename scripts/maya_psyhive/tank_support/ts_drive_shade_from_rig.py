"""Tools for using a shade asset to drive a rig geo.

This is used by Cache Tool to allow abcs to be generated with the
correct uvs.
"""

from maya import cmds
from pymel.core import nodetypes as nt

from psyhive import qt
from psyhive.tools import track_usage
from psyhive.utils import get_single, lprint

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_parent, set_namespace, del_namespace


def _clean_unused_uv_sets(mesh, verbose=0):
    """Clean unused uv sets from the given mesh.

    Args:
        mesh (HFnMesh): mesh to clean
        verbose (int): print process data
    """
    _all = cmds.polyUVSet(mesh, query=True, allUVSets=True) or []

    if len(_all) <= 1:
        lprint('NO UV CLEAN REQUIRED', verbose=verbose)
        return

    _cur = get_single(cmds.polyUVSet(mesh, query=True, currentUVSet=True))
    lprint('   - CLEANING UVS {} cur="{}" all={}'.format(mesh, _cur, _all),
           verbose=verbose)

    # Reorder if current is not default set (can't delete first set)
    if _all.index(_cur):
        lprint('     - SWITCHING SETS', _cur, _all[0], verbose=verbose)
        cmds.polyUVSet(mesh, reorder=True, uvSet=_cur, newUVSet=_all[0])

    for _idx, _set in enumerate(_all):
        if _set != _cur:
            lprint('     - DELETE SET', _idx, _set, verbose=verbose)
            cmds.polyUVSet(mesh, delete=True, uvSet=_set)


def _connect_visibility(src, trg, verbose=0):
    """Connect visibility of source to target node.

    If the source or any of its parents have driven visibility, these
    inputs are all used to drive the target node visibilty, via multiply
    nodes.

    Args:
        src (HFnMesh): source mesh
        trg (HFnMesh): target mesh
        verbose (int): print process data
    """

    # Find vis drivers
    _parents = src.find_parents()
    _vis_drivers = []
    for _parent in reversed(_parents):
        _vis_driver = _parent.visibility.find_driver()
        if _vis_driver:
            _vis_drivers.append(_vis_driver)

    _tail = src.visibility
    for _vis_driver in _vis_drivers:
        lprint(' - ADDING VIS DRIVER', _vis_driver, verbose=verbose)
        _tail = _tail.multiply_node(_vis_driver)
    _tail.connect(trg.visibility)


def get_shade_mb_for_rig(rig):
    """Get path to shade mb file for the given rig.

    Args:
        rig (RigRef): rig to map to shade file

    Returns:
        (str): path to shade file
    """
    from psyhive import tk2

    _rig_name = tk2.TTOutputName(rig.path)
    print ' - RIG NAME', _rig_name.path
    _task = {'rig': 'shade'}.get(_rig_name.task, _rig_name.task)
    print ' - TASK', _task
    _shade_name = _rig_name.map_to(
        Step='shade', output_type='shadegeo', Task=_task)
    print ' - SHADE NAME', _shade_name, _shade_name.data
    _shade_out = _shade_name.find_latest()
    if not _shade_out or not _shade_out.exists():
        raise RuntimeError("Failed to find shade for rig "+_rig_name.path)
    print ' - SHADE OUT', _shade_out.path
    _shade_file = _shade_out.find_file(extn='mb', format_='maya', catch=True)
    if not _shade_file:
        raise RuntimeError('Missing shade mb '+_shade_out.path)

    print ' - SHADE FILE', _shade_file
    return _shade_file


@track_usage
def drive_shade_geo_from_rig(cache_set, progress=False, verbose=0):
    """Use a rig to drive tmp geo duplicated from its shade asset.

    The shade asset is referenced into the scene, all meshes with
    corresponding meshes in the rig are duplicated and then attached
    to the rig geo using a blendshape. The shade asset is then removed.

    Args:
        cache_set (pm.ObjectSet): cache set from rig being cached
        progress (bool): show progress on bind
        verbose (int): print process data

    Returns:
        (HFnMesh list): list of driven shade geo
    """
    print 'DRIVE SHADE GEO FROM RIG'

    # Get anim rig
    _cache_set = cache_set or nt.ObjectSet(u'archer_rig2:bakeSet')
    print ' - CACHE SET', _cache_set
    if not _cache_set.referenceFile():
        print ' - NO CORRESPONDING RIG'
        raise RuntimeError("No rig found for {}".format(_cache_set))
    _rig = ref.find_ref(_cache_set.referenceFile().namespace)
    print ' - RIG', _rig
    print ' - RIG PATH', _rig.path

    # Find/import tmp shade asset
    _shade_file = get_shade_mb_for_rig(_rig)
    _shade = ref.create_ref(
        _shade_file.path, namespace='psyhive_tmp', force=True)

    # Duplicate geo and bind to rig
    _bake_geo = []
    _tmp_ns = ':tmp_{}'.format(_rig.namespace)
    set_namespace(_tmp_ns, clean=True)
    for _shade_mesh in qt.progress_bar(
            _shade.find_nodes(type_='mesh'), 'Binding {:d} geo{}',
            col='Tomato', show=progress):

        # Check there is equivalent mesh in rig
        if _shade_mesh.plug('intermediateObject').get_val():
            continue
        _shade_tfm = hom.HFnTransform(get_parent(_shade_mesh))
        try:
            _rig_tfm = _rig.get_node(_shade_tfm, class_=hom.HFnTransform)
        except ValueError:
            continue

        lprint(' - BINDING MESH', _shade_tfm, '->', _rig_tfm, verbose=verbose)

        # Duplicate mesh
        _dup = _shade_tfm.duplicate()
        lprint('   - DUPLICATING', _shade_tfm, verbose=verbose)
        _dup.parent(world=True)
        _clean_unused_uv_sets(_dup)
        _connect_visibility(_rig_tfm, _dup)
        _bake_geo.append(_dup)

        # Bind to rig
        _blend = hom.CMDS.blendShape(_rig_tfm, _dup)
        _blend.plug('origin').set_enum('world')
        _blend.plug('weight[0]').set_val(1.0)

    _shade.remove(force=True)
    cmds.namespace(set=":")

    if not _bake_geo:
        del_namespace(_tmp_ns)
        raise RuntimeError('No geo was attached - this means none of the '
                           'shade geo matched the rig bakeSet geo.')

    return _bake_geo, _bake_geo
