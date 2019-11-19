"""Tools for managing uv mesh components."""

from maya import cmds

from maya_psyhive.open_maya.cpnt_mesh import cm_base


class CpntUV(cm_base.CpntBase):
    """Represents a polygon UV."""

    def to_vals(self):
        """Get UV values.

        Returns:
            (float tuple): U/V values
        """
        return cmds.polyEditUV(self, query=True)
