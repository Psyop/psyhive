"""Tools for managing vertex components."""

from maya import cmds

from maya_psyhive.open_maya.point import HPoint
from maya_psyhive.open_maya.cpnt_mesh import cm_base


class CpntVtx(cm_base.CpntBase):
    """Represents a polygon vertex."""

    def to_p(self):
        """Get vertex world position.

        Returns:
            (HPoint): position
        """
        return HPoint(cmds.xform(
            self, query=True, translation=True, worldSpace=True))
