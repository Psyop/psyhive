"""Miscellaneous tools for supporting tank apps.

NOTE: this module should be deprecated in favour of
      maya_psyhive.tank_support (6/1/20).
"""

import os

from maya import cmds
from pymel.core import nodetypes as nt

from psyhive import qt, deprecate
from psyhive.tools import track_usage
from psyhive.utils import get_single, lprint, safe_zip

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_parent, reset_ns, set_namespace


def _clean_unused_uv_sets(mesh, verbose=0):
    """Clean unused uv sets from the given mesh.

    Args:
        mesh (HFnMesh): mesh to clean
        verbose (int): print process data
    """
    _all = cmds.polyUVSet(mesh, query=True, allUVSets=True)

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


@deprecate.deprecate_func('18/03/20 Use maya_psyhive.tank_support module')
@reset_ns
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
    from psyhive import tk2

    # Get anim rig
    _cache_set = cache_set or nt.ObjectSet(u'archer_rig2:bakeSet')
    print 'CACHE SET', _cache_set
    _rig = ref.find_ref(_cache_set.namespace().strip(':'))
    print 'RIG', _rig
    print 'RIG PATH', _rig.path

    # Find/import tmp shade asset
    _rig_out = tk2.TTOutputName(_rig.path)
    print 'RIG OUT', _rig_out.path
    _shade_out = _rig_out.map_to(
        Step='shade', output_type='shadegeo', Task='shade').find_latest()
    print 'SHADE OUT', _shade_out.path
    if not _shade_out.exists():
        raise RuntimeError("Missing shade file "+_shade_out.path)
    _shade_file = _shade_out.find_file(extn='mb', format_='maya')
    print 'SHADE FILE', _shade_file
    _shade = ref.create_ref(
        _shade_file.path, namespace='psyhive_tmp', force=True)

    # Duplicate geo and bind to rig
    _bake_geo = []
    _cleanup = []
    set_namespace(':tmp_{}'.format(_rig.namespace), clean=True)
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
        _cleanup.append(_dup)

        # Bind to rig
        _blend = hom.CMDS.blendShape(_rig_tfm, _dup)
        _blend.plug('origin').set_enum('world')
        _blend.plug('weight[0]').set_val(1.0)

    _shade.remove(force=True)

    return _bake_geo, _cleanup


@deprecate.deprecate_func('18/03/20 Use maya_psyhive.tank_support module')
@track_usage
def export_img_plane(camera, abc):
    """Export image plane preset data for the given camera/abc.

    Args:
        camera (str): camera shape node name
        abc (str): path to output abc
    """
    _cam = hom.HFnCamera(get_parent(str(camera)))
    lprint(' - CAM', _cam)

    # Read image plane
    _img_plane = get_single(
        _cam.shp.list_connections(type='imagePlane'), catch=True)
    if not _img_plane:
        lprint(' - NO IMAGE PLANE FOUND')
        return
    _img_plane = hom.HFnTransform(_img_plane.split('->')[-1])

    # Export preset for each shape
    for _shp in [_cam.shp, _img_plane.shp]:
        _preset = '{}/{}.preset'.format(
            os.path.dirname(abc), _shp.object_type())
        lprint(' - SAVING', _preset)
        _shp.save_preset(_preset)


@deprecate.deprecate_func('18/03/20 Use maya_psyhive.tank_support module')
@track_usage
def restore_img_plane(time_control, abc):
    """Restore image plane from preset data.

    Args:
        time_control (str): exocortex time control name
        abc (str): path to output abc
    """
    from psyhive import tk

    # Ignore non camera caches
    _abc = tk.get_output(abc)
    print 'ABC', _abc.path
    if _abc.output_type != 'camcache':
        print 'NOT A CAMERA CACHE'
        return

    # Make sure there are presets to apply
    _presets = []
    for _type in ['imagePlane', 'camera']:
        _preset = '{}/{}.preset'.format(_abc.dir, _type)
        if not os.path.exists(_preset):
            print 'MISSING PRESET', _preset
            return
        _presets.append(_preset)

    # Find camera node
    _time_ctrl = hom.HFnDependencyNode(time_control)
    _cam_shp = get_single(
        _time_ctrl.find_downstream(type_='camera', filter_=_abc.output_name),
        catch=True)
    if not _cam_shp:
        print 'NO CAM FOUND'
        return
    _cam = hom.HFnCamera(get_parent(_cam_shp))

    # Create image plane and apply presets
    _img_plane = hom.CMDS.imagePlane(camera=_cam)
    for _preset, _shp in safe_zip(_presets, [_img_plane.shp, _cam.shp]):
        _shp.load_preset(_preset)
