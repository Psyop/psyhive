"""Tools for managing points."""

from maya import cmds
from maya.api import OpenMaya as om

from maya_psyhive.open_maya.array3 import HArray3Base


class HPoint(HArray3Base, om.MPoint):
    """Represents a point in 3d space."""


def get_p(node):
    """Get position of the given node.

    Args:
        node (str): node to read

    Returns:
        (HPoint): node position
    """
    _xform = HPoint(
        cmds.xform(node, query=True, translation=True, worldSpace=True))
    return _xform


ORIGIN = HPoint()
