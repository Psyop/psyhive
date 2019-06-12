"""Tools for managing anim curves."""

from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma

from maya_psyhive.open_maya.base_node import BaseNode


class HFnAnimCurve(BaseNode, oma.MFnAnimCurve):
    """Wrapper for MFnAnimCurve object."""

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): anim curve node
        """
        super(HFnAnimCurve, self).__init__(node)
        _tmp_list = om.MSelectionList()
        _tmp_list.add(node)
        _obj = _tmp_list.getDependNode(0)
        oma.MFnAnimCurve.__init__(self, _obj)

    def set_tangents(self, type_):
        """Set all tangents on this curve.

        Args:
            type_ (str): tangent type
        """
        cmds.keyTangent(self, inTangentType=type_, outTangentType=type_)
