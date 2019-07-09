"""Tools for blasting the scene and checking for rigs outside camera."""

import copy

from maya import cmds

from psyhive import tk, py_gui
from psyhive.utils import lprint, passes_filter, ints_to_str
from hv_test import dev

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.tools.frustrum_test_blast import remove_rigs
from maya_psyhive.utils import cycle_check, is_visible


class _Rig(ref.FileRef):
    """Represents a rig referenced into a scene."""

    def __init__(self, ref_node):
        """Constructor.

        Args:
            ref_node (str): reference node
        """
        super(_Rig, self).__init__(ref_node)
        self.asset = tk.TTAssetOutputFile(self.path)
        if self.asset.sg_asset_type == 'camera':
            raise ValueError('Camera is not rig')
        for _node in ['bakeSet']:
            try:
                self.get_node(_node)
            except RuntimeError:
                raise ValueError("Missing node "+_node)

    def get_geos(self):
        """Get a list of geos to test.

        Mouth geo seems to give bad bbox results so is ignored.

        Returns:
            (str list): visibile geos
        """
        return [
            _geo for _geo in cmds.sets(self.get_node('bakeSet'), query=True)
            if is_visible(_geo) and
            passes_filter(_geo, '-_eye_Geo -_tongue_Geo -_teeth_Geo')]


@dev.print_dur
def _blast_and_find_rigs_outside_frustrum(
        cam, rigs, kwargs, sample_freq, verbose=1):
    """Execute blast, checking to find rigs outside frustrum.

    Args:
        cam (HFnCamera): camera being blasted through
        rigs (FileRef list): list of rigs to check
        kwargs (dict): playblast kwargs
        sample_freq (int): frame gap between frustrum tests - ie. a value
            of 5 means the frustrum is sampled every 5 frames
        verbose (int): print process data

    Returns:
        (FileRef list): list of rigs outside frustrum
    """
    _frames = kwargs.pop('frame')
    _check_frames = range(_frames[0], _frames[-1]+1, sample_freq)

    # Blast scene and test rigs in camera
    _off_cam_rigs = copy.copy(rigs)
    while _check_frames:

        _frame = _check_frames.pop(0)

        lprint(' - CHECKING FRAME', _frame, verbose=verbose)
        cmds.currentTime(_frame)

        # Remove rigs in camera from list
        lprint(
            ' - TESTING {:d} RIGS'.format(len(_off_cam_rigs)),
            _off_cam_rigs, verbose=verbose)
        for _rig in copy.copy(_off_cam_rigs):
            if _rig_in_cam(cam, _rig):
                lprint(' - RIG IN CAMERA:', _rig, verbose=verbose)
                _off_cam_rigs.remove(_rig)

        # Blast frames
        if not _off_cam_rigs:
            lprint(' - NO RIGS LEFT TO CHECK', verbose=verbose)
            _check_frames = []
            _blast_frames = range(_frame, _frames[-1]+1)
        else:
            _blast_frames = range(_frame, _frame+sample_freq)
        lprint(
            ' - BLASTING FRAMES', ints_to_str(_blast_frames), verbose=verbose)
        cmds.playblast(frame=_blast_frames, **kwargs)

    return _off_cam_rigs


def _rig_in_cam(cam, rig):
    """Test if the given rig is inside the camera frustrum.

    Combining the geo is slightly quicker, but testing each geo separately
    is much more accurate, and you don't have to worry about separateable
    objects like fish or swords or bows. The speed difference was only
    48s for the combined and 52s for the separate (without the frustrum test
    the blast took 41s).

    Args:
        cam (HFnCamera): camera to test against
        rig (FileRef): rig to check

    Returns:
        (bool): whether rig is inside camera frustrum
    """
    _geos = rig.get_geos()
    for _geo in _geos:
        _bbox = hom.get_bbox(_geo)
        if cam.contains(_bbox):
            return True

    return False


@py_gui.hide_from_gui
def blast_with_frustrum_check(kwargs, sample_freq=5):
    """Blast and check rigs in frustrum.

    Args:
        kwargs (dict): playblast kwargs
        sample_freq (int): frame gap between frustrum tests - ie. a value
            of 5 means the frustrum is sampled every 5 frames
    """
    cycle_check()

    _cam = hom.get_active_cam()
    _rigs = ref.find_refs(class_=_Rig)
    _off_cam_rigs = _blast_and_find_rigs_outside_frustrum(
        _cam, _rigs, kwargs, sample_freq=sample_freq)
    print '{}/{} RIGS ARE OFF CAMERA'.format(len(_off_cam_rigs), len(_rigs))

    # Remove off cam rigs
    if _off_cam_rigs:
        remove_rigs.launch(_off_cam_rigs)
