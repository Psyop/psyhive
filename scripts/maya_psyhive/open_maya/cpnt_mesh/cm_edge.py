"""Tools for managing edge components."""

from maya_psyhive.open_maya.plane import HPlane
from maya_psyhive.open_maya.vector import HVector
from maya_psyhive.open_maya.cpnt_mesh import cm_base


class CpntEdge(cm_base.CpntBase):
    """Represents a polygon edge."""

    def intersection(self, other):
        """Find the intersection of this edge with another object.

        Args:
            other (any): object to compare with

        Returns:
            (HPoint): intersection
        """
        if isinstance(other, HPlane):
            return self._intersection_plane(other)
        raise ValueError(other)

    def _intersection_plane(self, plane):
        """Find this edge's intersection with a plane (assumes intersection).

        Args:
            plane (HPlane): plane to intersect

        Returns:
            (HPoint): intersection point
        """
        _pts = [_vtx.to_p() for _vtx in self.to_vtxs()]
        _dists = [plane.distanceToPoint(HVector(_pt)) for _pt in _pts]
        _vect = _pts[1] - _pts[0]
        return _pts[0] + _vect*(_dists[0]/sum(_dists))

    def intersects(self, other):
        """Test if this edge intersects another object.

        Args:
            other (any): object to compare with

        Returns:
            (bool): whether there is an intersection
        """
        if isinstance(other, HPlane):
            return self._intersects_plane(other)
        raise ValueError(other)

    def _intersects_plane(self, plane):
        """Test if this edge intersects a plane.

        Args:
            plane (HPlane): plane to test

        Returns:
            (bool): whether there is an intersection
        """

        _pts = [_vtx.to_p() for _vtx in self.to_vtxs()]
        return len(set([plane.contains(_pt) for _pt in _pts])) != 1

    def to_v(self):
        """To vector.

        Returns:
            (HVector): this edge's vector
        """
        _pts = [_vtx.to_p() for _vtx in self.to_vtxs()]
        return _pts[1] - _pts[0]
