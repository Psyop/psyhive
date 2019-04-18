"""Tools for managing 3d vectors."""

from maya import cmds
from maya.api import OpenMaya as om

from maya_psyhive.open_maya.utils import HArray3Base, cast_result
from maya_psyhive.utils import set_col


class HVector(HArray3Base, om.MVector):
    """Represents a 3d vector."""

    __mul__ = cast_result(om.MVector.__mul__)
    __neg__ = cast_result(om.MVector.__neg__)
    __xor__ = cast_result(om.MVector.__xor__)

    def build_crv(self, pos, col=None, name='HVector'):
        """Build a curve to display this vector.

        Args:
            pos (HPoint): start point of vector
            col (str): vector colour
            name (str): name for vector geo
        """
        _end = pos+self
        _crv = cmds.curve(
            point=[pos.to_tuple(), _end.to_tuple()],
            degree=1, name=name)
        if col:
            set_col(_crv, col)
        return _crv

    def normalized(self):
        """Get the normalized version of this vector."""
        _dup = HVector(self)
        _dup.normalize()
        return _dup


X_AXIS = HVector(1, 0, 0)
Y_AXIS = HVector(0, 1, 0)
Z_AXIS = HVector(0, 0, 1)
