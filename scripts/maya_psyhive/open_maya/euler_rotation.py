"""Tools for managing euler rotations."""

import math

from maya import cmds
from maya.api import OpenMaya as om

from maya_psyhive.open_maya.utils import cast_result


class HEulerRotation(om.MEulerRotation):
    """Wrapper for OpenMaya.MEulerRotation class."""

    as_mtx = cast_result(om.MEulerRotation.asMatrix)

    def apply_to(self, node):
        """Apply these rotations to the given node.

        Args:
            node (str): node to apply rotations to
        """
        _degrees = [math.degrees(_val) for _val in self]
        cmds.setAttr(node+'.rotateOrder', self.order)
        cmds.xform(node, rotation=_degrees, worldSpace=True)


def get_r(node):
    """Get euler rotations for the given node.

    Args:
        node (str): node to read

    Returns:
        (HEulerRotation): rotations
    """
    _rot = cmds.xform(node, query=True, rotation=True, worldSpace=True)
    return HEulerRotation(*[math.radians(_val) for _val in _rot])
