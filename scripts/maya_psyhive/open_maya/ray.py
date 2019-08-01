"""Tools for managing rays."""


class HVRay(object):
    """Represents a an infinte ray.

    This is not represented in OpenMaya so have HV (virtual) prefix.

    The ray is defined by a point and a vector direction.
    """

    def __init__(self, pnt, vec):
        """Constructor.

        Args:
            pnt (HPoint): point
            vec (HVector): vector
        """
        self.pnt = pnt
        self.vec = vec.normalized()

    def build_geo(self, name='ray', col="red", scale=1.0):
        """Build geo in maya to represent this ray.

        Args:
            name (str): name for geo grp
            col (str): colour for geo
            scale (float): geo scale
        """
        from maya_psyhive import open_maya as hom
        _ly = self.vec
        _lz = _ly ^ hom.Y_AXIS
        _lx = _lz ^ _ly

        for _pts in [
                [
                    self.pnt,
                    self.pnt+_ly*scale*3,
                    self.pnt+_ly*scale*3+(_lx-_ly)*scale],
                [
                    self.pnt+_ly*scale*3,
                    self.pnt+_ly*scale*3+(-_lx-_ly)*scale]]:
            _crv = hom.CMDS.curve(
                point=[_pt.to_tuple() for _pt in _pts], degree=1)
            _crv.set_col(col=col)
            _crv.add_to_grp(name+"_GRP")

        _crv = hom.CMDS.circle(
            center=self.pnt, normal=self.vec, radius=scale,
            constructionHistory=False)
        _crv.set_col(col=col)
        _crv.add_to_grp(name+"_GRP")

    def intersection(self, other):
        """Find intersection between this ray and another object.

        Args:
            other (any): object to compare with

        Returns:
            (any): intersections
        """
        from maya_psyhive import open_maya as hom
        if isinstance(other, hom.HFnMesh):
            return other.intersection(self)
        raise ValueError(other)

    def to_plane(self):
        """Get the equivalent plane to this ray.

        Returns:
            (HPlane): plane object
        """
        from maya_psyhive import open_maya as hom
        return hom.HPlane(self.pnt, self.vec)
