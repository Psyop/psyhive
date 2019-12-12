"""Tools for managing euler rotations."""

import math

from maya import cmds
from maya.api import OpenMaya as om

from maya_psyhive.open_maya.utils import cast_result


class HEulerRotation(om.MEulerRotation):
    """Wrapper for OpenMaya.MEulerRotation class."""

    as_mtx = cast_result(om.MEulerRotation.asMatrix)

    def apply_to(self, node, relative=False):
        """Apply these rotations to the given node.

        Args:
            node (str): node to apply rotations to
            relative (bool): apply relative to current rot
        """
        _degrees = [math.degrees(_val) for _val in self]
        if not relative:
            cmds.setAttr(str(node)+'.rotateOrder', self.order)
            cmds.xform(node, rotation=_degrees, worldSpace=True)
        else:
            cmds.rotate(_degrees[0], _degrees[1], _degrees[2], node,
                        relative=True)

    def as_vect(self):
        """Get this rotation as a vector.

        This is equivalent to a unit vector on the z (forward) axis
        had this rotation applied.

        Returns:
            (HVector): vector
        """
        from maya_psyhive import open_maya as hom
        _vect = hom.Z_AXIS
        return _vect.rotate_by(self)

    def to_tuple(self):
        """Get rot values as tuple.

        Returns:
            (float tuple): xyz values
        """
        return (self.x, self.y, self.z)

    def __neg__(self):
        return HEulerRotation(super(HEulerRotation, self).__neg__())

    def __str__(self):
        _order = {0: 'XYZ'}[self.order]
        return '<{}[{}]({:.05f}, {:.05f}, {:.05f})>'.format(
            type(self).__name__, _order, self.x, self.y, self.z)

    def __sub__(self, other):
        return HEulerRotation(super(HEulerRotation, self).__sub__(other))

    __repr__ = __str__


def get_r(node):
    """Get euler rotations for the given node.

    Args:
        node (str): node to read

    Returns:
        (HEulerRotation): rotations
    """
    _rot = cmds.xform(node, query=True, rotation=True, worldSpace=True)
    return HEulerRotation(*[math.radians(_val) for _val in _rot])
