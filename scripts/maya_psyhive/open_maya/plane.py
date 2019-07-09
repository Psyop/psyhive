"""Tools for managing planes.

A plane is defined as a point and a normal, although OpenMaya stores the
information as a normal and the distance from the origin.
"""

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint
from maya_psyhive.utils import get_unique


class HPlane(om.MPlane):
    """Represents a plane in 3d space."""

    def __init__(self, pos, nml, name='plane'):
        """Constructor.

        Args:
            pos (HPoint): point
            nml (HVector): normal
            name (str): name of plane (for debugging)
        """
        from maya_psyhive import open_maya as hom

        self.pos = pos
        self.nml = nml.normalized()
        self.name = name

        _to_orig = hom.ORIGIN - self.pos
        self.dist = _to_orig * self.nml

        om.MPlane.__init__(self)
        self.setPlane(self.nml[0], self.nml[1], self.nml[2], self.dist)

    def build_geo(self, lx_=None, name=None, col='green'):
        """Build geo to represent this plane in the viewport.

        Args:
            lx_ (HVector): override local x for geo
            name (str): name for geo transform
            col (str): curve colour

        Returns:
            (HFnNurbsCurve): curve
        """
        from maya_psyhive import open_maya as hom

        _name = get_unique(name or self.name)
        _lx = lx_ or self.nml ^ hom.X_AXIS
        _mtx = hom.axes_to_m(pos=self.pos, lx_=_lx, ly_=self.nml)
        _sq = hom.square(name=_name)
        _sq.u_scale(0.4)
        _sq.flush()
        _mtx.apply_to(_sq)

        _arrow = hom.build_arrow(length=0.2)
        _mtx.apply_to(_arrow)
        cmds.parent(_arrow.shp, _sq, shape=True, relative=True)
        _arrow.delete()
        _sq.set_col(col)

        return _sq

    def contains(self, other):
        """Test if this plane contains another object.

        This is true if the entire object falls inside this plane, ie. the
        whole object is on the side away from the normal.

        Args:
            other (any): object to compare

        Returns:
            (bool): whether plane contains object
        """
        from maya_psyhive import open_maya as hom
        if isinstance(other, hom.HBoundingBox):
            return self.contains_bbox(other)
        elif isinstance(other, hom.HPoint):
            return self.contains_point(other)
        raise ValueError(other)

    def contains_bbox(self, bbox, verbose=0):
        """Test if the whole of this bounding box is inside the plane.

        For this to be true, all of the corner points need to be
        inside the plane.

        Args:
            bbox (HBoundingBox): bounding box to test
            verbose (int): print process data

        Returns:
            (bool): whether this plane contains the bbox
        """
        for _pt in bbox.get_corners():
            _contained = self.contains(_pt)
            if not _contained:
                return False
            lprint(' -', _pt, _contained, verbose=verbose)
        return True

    def contains_point(self, pos, build_crv=False):
        """Test whether a point falls inside this plane.

        This means the point is below the plane - and points above
        (ie. in the direction of the normal) are considered below.

        Args:
            pos (HPoint): point to test
            build_crv (bool): build debug curve

        Returns:
            (bool): whether this plane contains the point
        """

        _vect = pos - self.pos
        if build_crv:
            _vect.build_crv(self.pos)
        return _vect * self.nml < 0

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.name)
