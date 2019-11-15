"""Tools for managing face components."""

from maya_psyhive.open_maya.bounding_box import get_bbox
from maya_psyhive.open_maya.plane import HPlane
from maya_psyhive.open_maya.point import HPoint
from maya_psyhive.open_maya.cpnt_mesh import cm_base


class CpntFace(cm_base.CpntBase):
    """Represents a polygon face."""

    def bbox(self):
        """Get bouding box of this face.

        Returns:
            (HBoundingBox): bounding box
        """
        _vtxs = self.to_vtxs()
        _pts = [_vtx.to_p() for _vtx in _vtxs]
        return get_bbox(_pts)

    def to_c(self):
        """Get face centre.

        Returns:
            (HPoint): centre point
        """
        _pts = [_vtx.to_p() for _vtx in self.to_vtxs()]
        return sum(_pts, HPoint())/len(_pts)

    def to_n(self):
        """Get face normal.

        Returns:
            (HVector): normal
        """
        _edges = self.to_edges()[:2]
        _vects = [_edge.to_v() for _edge in self.to_edges()]
        return (_vects[0] ^ _vects[1]).normalized()

    def to_plane(self):
        """Convert to plane.

        Returns:
            (HPlane): face plane
        """
        _pos = self.to_vtxs()[0].to_p()
        _nml = self.to_n()
        return HPlane(pos=_pos, nml=_nml)
