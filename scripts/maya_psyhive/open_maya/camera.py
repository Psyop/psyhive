"""Tools for managing cameras."""

import math

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import safe_zip, lprint
from maya_psyhive import ui
from maya_psyhive.utils import get_parent

from maya_psyhive.open_maya.base_transform import BaseTransform
from maya_psyhive.open_maya.dag_path import HDagPath


class HFnCamera(BaseTransform, om.MFnCamera):
    """Represent a nurbs curve."""

    def __init__(self, tfm):
        """Constructor.

        Args:
            tfm (str): curve transform
        """
        self.tfm = tfm
        super(HFnCamera, self).__init__(self.tfm)
        if not self.shp:
            raise RuntimeError('Missing shape '+tfm)
        _dag_path = HDagPath(self.shp.node)
        om.MFnCamera.__init__(self, _dag_path)

    def build_geo(self):
        """Build geo to represent this frustrum.

        Returns:
            (HFnMesh): frustrum mesh
        """
        from maya_psyhive import open_maya as hom

        hom.LOC_SCALE = 0.3
        _cube = hom.CMDS.polyCube(name='frustrum')

        _corners = []
        for _z_depth in [1, 10]:
            _corners += self.get_depth_rect(_z_depth)
        for _vtx, _corner in safe_zip([2, 3, 0, 1, 4, 5, 6, 7], _corners):
            _corner.apply_to(_cube.vtx[_vtx])

        return _cube

    def contains(self, other):
        """Test if the camera frustrum contains the given object.

        This is definted as any part of the object appearing within
        the camera frustrum.

        Args:
            other (any): object to compare with

        Returns:
            ():
        """
        from maya_psyhive import open_maya as hom
        if isinstance(other, hom.HBoundingBox):
            return self.contains_bbox(other)
        raise ValueError(other)

    def contains_bbox(self, bbox, verbose=0):
        """Test if this camera frustrum contains the given bbox.

        This is true at least one corner of the bounding box falls inside
        all of the bounding planes.

        Args:
            bbox (HBoundingBox): bbox to check
            verbose (int): print process data

        Returns:
            (bool): whether bbox falls inside this camera
        """
        _planes = self.get_bounding_planes()
        lprint('TESTING PLANES', verbose=verbose)
        for _plane in _planes:
            _inside = bbox.inside(_plane)
            lprint(' - TESTING', _plane, _inside, verbose=verbose)
            if not _inside:
                return False
        return True

    def get_bounding_planes(self, far=False, depth=5.0, build_geo=False):
        """Get bounding planes defining the frustrum.

        Args:
            far (bool): add far plane
            depth (float): depth to build side planes at (this is
                only asthetic)
            build_geo (bool): build planes geo

        Returns:
            (HPlane list): list of planes
        """
        from maya_psyhive import open_maya as hom
        _tl, _bl, _tr, _br = self.get_depth_rect(depth=depth)
        _mtx = self.get_m()

        # Build top/bottom/left/right planes
        _planes = []
        for _pt_a, _pt_b, _lx, _name in [
                (_tl, _tr, _mtx.lx_(), 'top'),
                (_bl, _br, -_mtx.lx_(), 'bottom'),
                (_tl, _bl, -_mtx.ly_(), 'left'),
                (_tr, _br, _mtx.ly_(), 'right'),
        ]:
            _pos = (_pt_a + _pt_b)/2
            _vect = (_mtx.pos() - _pos) ^ _lx
            _plane = hom.HPlane(pos=_pos, nml=_vect, name=_name)
            if build_geo:
                _plane.build_geo(lx_=(_pos-_mtx.pos()).normalized())
            _planes.append(_plane)

        # Build near plane
        _near_clip = self.shp.plug('nearClipPlane').get_val()
        _nml = _mtx.lz_()
        _near = hom.HPlane(
            pos=_mtx.pos()-_nml*_near_clip, nml=_nml, name='near')
        if build_geo:
            _near.build_geo(lx_=_mtx.lx_())
        _planes.append(_near)

        if far:
            raise NotImplementedError

        return _planes

    def get_depth_rect(self, depth):
        """Get points defining a depth plane.

        Each point is a corner of the view: top left, bottom left, top right,
        bottom right.

        Args:
            depth (float): depth of plane

        Returns:
            (HPoint list): 4 points
        """
        _mtx = self.get_m()
        _hfv = math.radians(
            cmds.camera(self, query=True, horizontalFieldOfView=True))
        _vfv = math.radians(
            cmds.camera(self, query=True, verticalFieldOfView=True))
        _corners = []
        for _x_mult in [1, -1]:
            _x_len = depth * math.tan(_hfv/2)
            for _y_mult in [1, -1]:
                _y_len = depth * math.tan(_vfv/2)

                _x_cpnt = _mtx.lx_() * _x_mult * _x_len
                _y_cpnt = _mtx.ly_() * _y_mult * _y_len
                _z_cpnt = -_mtx.lz_() * depth

                _corner = _mtx.pos() + _x_cpnt + _y_cpnt + _z_cpnt
                _corners.append(_corner)

        _tl, _bl, _tr, _br = _corners
        return _tl, _bl, _tr, _br


def get_active_cam():
    """Get camera from the curret active viewport.

    Returns:
        (HFnCamera): active camera
    """
    _model = ui.get_active_model_panel()
    _cam_node = cmds.modelPanel(_model, query=True, camera=True)
    if cmds.objectType(_cam_node) == 'camera':
        _cam = HFnCamera(get_parent(_cam_node))
    else:
        _cam = HFnCamera(_cam_node)
    return _cam
