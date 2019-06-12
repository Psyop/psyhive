"""Tools for managing bounding boxes."""

from maya import cmds
from maya.api import OpenMaya as om

import six

from psyhive.utils import lprint
from maya_psyhive.utils import get_unique, set_col


class HBoundingBox(om.MBoundingBox):
    """Represents a bounding box."""

    def _corner_ps(self):
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

    def build_cube(self, name="bbox", col=None):
        """Build cube geo to represent this bbox.

        Args:
            name (str): name for geo
            col (str): cube colour

        Returns:
            (str): cube geo
        """
        _cube = cmds.polyCube(name=get_unique(name))[0]
        if col:
            set_col(_cube, col)

        # Move points into pos
        _pts = self._corner_ps()
        for _idx in range(8):
            cmds.xform(
                "{}.vtx[{:d}]".format(_cube, _idx),
                translation=_pts[_idx].to_tuple(), worldSpace=True)

        return _cube

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


def get_bbox(obj, verbose=0):
    """Get bbox for the given data.

    Args:
        obj (list|HPoint|HVector|str): input data
        verbose (int): print process data

    Returns:
        (HBoundingBox): bounding box
    """
    from maya_psyhive import open_maya as hom

    if isinstance(obj, list):
        _bboxes = [get_bbox(_obj) for _obj in obj]
        return sum(_bboxes[1:], _bboxes[0])
    elif isinstance(obj, hom.HPoint):
        return HBoundingBox(obj, obj)
    elif isinstance(obj, hom.HVector):
        _pt = hom.HPoint(obj)
        return HBoundingBox(_pt, _pt)
    elif isinstance(obj, (six.string_types, hom.HFnNurbsCurve)):
        _result = cmds.exactWorldBoundingBox(
            obj, calculateExactly=True, ignoreInvisible=True)
        lprint('BBOX RESULT', _result, verbose=verbose)
        _min = hom.HPoint(_result[:3])
        _max = hom.HPoint(_result[-3:])
        return HBoundingBox(_min, _max)
    else:
        raise ValueError('Failed to create bounding box {} ({})'.format(
            obj, type(obj).__name__))
