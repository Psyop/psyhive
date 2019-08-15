"""Tools for managing 3d vectors."""

import math

from maya import cmds
from maya.api import OpenMaya as om

from maya_psyhive.open_maya.utils import cast_result
from maya_psyhive.open_maya.base_array3 import BaseArray3
from maya_psyhive.utils import set_col, get_unique


class HVector(BaseArray3, om.MVector):
    """Represents a 3d vector."""

    __mul__ = cast_result(om.MVector.__mul__)
    __neg__ = cast_result(om.MVector.__neg__)
    __xor__ = cast_result(om.MVector.__xor__)

    def as_mtx(self):
        """Get this vector as a transformation matrix.

        Returns:
            (HMatrix): matrix
        """
        from maya_psyhive import open_maya as hom
        _vals = list(hom.HMatrix().to_tuple())
        for _idx in range(3):
            _vals[12+_idx] = self[_idx]
        return hom.HMatrix(_vals)

    def build_crv(self, pos=None, col=None, name='HVector'):
        """Build a curve to display this vector.

        Args:
            pos (HPoint): start point of vector
            col (str): vector colour
            name (str): name for vector geo
        """
        from maya_psyhive import open_maya as hom
        _pos = pos or HVector()
        _end = _pos+self
        _crv = cmds.curve(
            point=[_pos.to_tuple(), _end.to_tuple()],
            degree=1, name=get_unique(name))
        if col:
            set_col(_crv, col)
        return hom.HFnNurbsCurve(_crv)

    def get_bearing(self):
        """Get bearing of this vector.

        This is the angle the vector makes in the XZ plane from the z axis
        facing downwards (ie. in -Y direction). The result is clamped in
        the range 0-360.

        Returns:
            (float): bearing
        """
        if not self.z:
            _bearing = 270 if self.x > 0 else 90
        else:
            _bearing_r = math.atan(self.x/self.z)
            _bearing = math.degrees(_bearing_r) % 360

        if self.z < 0:
            _bearing -= 180
            _bearing = _bearing % 360
        return _bearing

    def get_pitch(self, build_geo=False):
        """Get pitch of this vector.

        The is the angle which it makes with the horizontal. The result
        is clamped in the range 0-360.

        Args:
            build_geo (bool): build test geo

        Returns:
            (float): pitch
        """
        _side = (self ^ Y_AXIS).normalized()
        _base = -(_side ^ Y_AXIS).normalized()
        _result = math.degrees(_base.angle(self))
        if self.y < 0:
            _result = -_result
        if build_geo:
            self.build_crv(col='red')
            _side.build_crv(col='green')
            _base.build_crv(col='blue')
        return _result % 360

    def normalized(self):
        """Get the normalized version of this vector."""
        _dup = HVector(self)
        _dup.normalize()
        return _dup

    def rotate_by(self, rot):
        """Apply the given rotation to this vector.

        Args:
            rot (HEulerRotation|MQuaternion): rotation to apply

        Returns:
            (HVector): rotated vector
        """
        return HVector(self.rotateBy(rot))


X_AXIS = HVector(1, 0, 0)
Y_AXIS = HVector(0, 1, 0)
Z_AXIS = HVector(0, 0, 1)
