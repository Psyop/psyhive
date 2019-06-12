"""Tools for managing transform nodes."""

from maya.api import OpenMaya as om

from maya_psyhive.open_maya.dag_path import HDagPath
from maya_psyhive.open_maya.base_transform import BaseTransform


class HFnTransform(BaseTransform, om.MFnTransform):
    """Wrapper for MFnTransform object."""

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): transform node name
        """
        self.node = node
        super(HFnTransform, self).__init__(node)
        _dag_path = HDagPath(self.node)
        om.MFnTransform.__init__(self, _dag_path)
