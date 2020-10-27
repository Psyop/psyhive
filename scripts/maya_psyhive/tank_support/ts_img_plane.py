"""Tools for managing the export/import of camera image planes.

This is used by Cache Tool and Asset Manager.
"""

import os

from psyhive.tools import track_usage
from psyhive.utils import get_single, lprint, safe_zip

from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_parent


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
        try:
            _shp.save_preset(_preset)
        except RuntimeError:
            lprint(' - FAILED TO SAVE')


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
