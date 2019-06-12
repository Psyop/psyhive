"""Tools for managing nurbs surfaces."""

from maya.api import OpenMaya as om

from maya_psyhive.open_maya.base_transform import BaseTransform
from maya_psyhive.open_maya.dag_path import HDagPath


class HFnNurbsSurface(BaseTransform, om.MFnNurbsSurface):
    """Represent a nurbs surface."""

    def __init__(self, tfm):
        """Constructor.

        Args:
            tfm (str): surface transform
        """
        self.tfm = tfm
        super(HFnNurbsSurface, self).__init__(self.tfm)
        _dag_path = HDagPath(self.shp.node)
        om.MFnNurbsSurface.__init__(self, _dag_path)
        self.world_space = self.shp.plug('worldSpace')
        self.create = self.shp.plug('create')
