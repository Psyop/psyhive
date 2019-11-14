"""Tools for managing bounding boxes."""

from maya import cmds
from maya.api import OpenMaya as om

import six

from psyhive.utils import lprint


class HBoundingBox(om.MBoundingBox):
    """Represents a bounding box."""

    def build_cube(self, name="bbox", col=None, verbose=0):
        """Build cube geo to represent this bbox.

        Args:
            name (str): name for geo
            col (str): cube colour
            verbose (int): print process data

        Returns:
            (HFnMesh): cube geo
        """
        from maya_psyhive import open_maya as hom
        _cube = hom.CMDS.polyCube(name=name)
        if col:
            _cube.set_col(col)

        # Move points into pos
        _pts = self.get_corners()
        for _idx, _pt in enumerate(_pts):
            _vtx = _cube.vtx[_idx]
            lprint(' - APPLYING VTX', _vtx, _pt, verbose=verbose)
            cmds.xform(
                _vtx, translation=_pt.to_tuple(), worldSpace=True)

        return _cube

    @property
    def center(self):
        """Get bbox centrepoint.

        Returns:
            (HPoint): centre
        """
        from maya_psyhive import open_maya as hom
        return hom.HPoint(super(HBoundingBox, self).center)

    def get_corners(self):
        """Get list of 8 corner points.

        Returns:
            (HPoint list): corners
        """
        from maya_psyhive import open_maya as hom
        _min = hom.HPoint(self.min)
        _max = hom.HPoint(self.max)

        return [
            hom.HPoint(_min[0], _min[1], _max[2]),
            hom.HPoint(_max[0], _min[1], _max[2]),
            hom.HPoint(_min[0], _max[1], _max[2]),
            hom.HPoint(_max[0], _max[1], _max[2]),

            hom.HPoint(_min[0], _max[1], _min[2]),
            hom.HPoint(_max[0], _max[1], _min[2]),
            hom.HPoint(_min[0], _min[1], _min[2]),
            hom.HPoint(_max[0], _min[1], _min[2])]

    def inside(self, other):
        """Test if this bbox is inside another object.

        This is defined as all or part of this bbox being inside
        the other object.

        Args:
            other (any): object to test against

        Returns:
            (bool): whether this bbox is inside
        """
        from maya_psyhive import open_maya as hom
        if isinstance(other, hom.HPlane):
            return self.inside_plane(other)
        raise ValueError(other)

    def inside_plane(self, plane):
        """Test if this bbox falls inside the given plane.

        This is defined as at least one corner falling inside the plane.

        Args:
            plane (HPlane): plane to test against

        Returns:
            (bool): whether this bbbox is inside the plane
        """
        for _corner in self.get_corners():
            if plane.contains(_corner):
                return True
        return False

    @property
    def max(self):
        """Get bbox max point.

        Returns:
            (HPoint): max
        """
        from maya_psyhive import open_maya as hom
        return hom.HPoint(super(HBoundingBox, self).max)

    @property
    def min(self):
        """Get bbox min point.

        Returns:
            (HPoint): min
        """
        from maya_psyhive import open_maya as hom
        return hom.HPoint(super(HBoundingBox, self).min)

    def size(self):
        """Get size of this bbox.

        Returns:
            (HVector): bbox size
        """
        return self.max - self.min

    def __add__(self, other):
        from maya_psyhive import open_maya as hom
        if not isinstance(other, om.MBoundingBox):
            raise TypeError(other)
        _s_min, _o_min = self.min, other.min
        _s_max, _o_max = self.max, other.max
        _min = hom.HPoint(
            min([_s_min.x, _o_min.x]),
            min([_s_min.y, _o_min.y]),
            min([_s_min.z, _o_min.z]))
        _max = hom.HPoint(
            max([_s_max.x, _o_max.x]),
            max([_s_max.y, _o_max.y]),
            max([_s_max.z, _o_max.z]))
        return HBoundingBox(_min, _max)

    def __repr__(self):
        return "<{}>".format(type(self).__name__)


def get_bbox(obj, ignore_points=False, verbose=0):
    """Get bbox for the given data.

    Args:
        obj (list|HPoint|HVector|str): input data
        ignore_points (bool): ignore components with zero size bboxes
            (for lists of objects)
        verbose (int): print process data

    Returns:
        (HBoundingBox): bounding box
    """
    from maya_psyhive import open_maya as hom

    if isinstance(obj, list):
        _bboxes = [get_bbox(_obj) for _obj in obj]
        if ignore_points:
            _bboxes = [_bbox for _bbox in _bboxes if _bbox.size().length()]
        return sum(_bboxes[1:], _bboxes[0])
    elif isinstance(obj, hom.HPoint):
        return HBoundingBox(obj, obj)
    elif isinstance(obj, hom.HVector):
        _pt = hom.HPoint(obj)
        return HBoundingBox(_pt, _pt)
    elif isinstance(obj, (
            six.string_types, hom.HFnDependencyNode)):
        _result = cmds.exactWorldBoundingBox(
            obj, calculateExactly=True, ignoreInvisible=True)
        lprint('BBOX RESULT', _result, verbose=verbose)
        _min = hom.HPoint(_result[:3])
        _max = hom.HPoint(_result[-3:])
        return HBoundingBox(_min, _max)
    else:
        raise ValueError('Failed to create bounding box {} ({})'.format(
            obj, type(obj).__name__))
