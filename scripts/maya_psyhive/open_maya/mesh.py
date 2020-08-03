"""Tools for managing polygon meshes."""

import copy

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint, get_single

from maya_psyhive.open_maya.utils import IndexedAttrGetter, get_unique
from maya_psyhive.open_maya.base_transform import BaseTransform
from maya_psyhive.open_maya.dag_path import HDagPath


class HFnMesh(BaseTransform, om.MFnMesh):
    """Represent a nurbs curve."""

    def __init__(self, tfm):
        """Constructor.

        Args:
            tfm (str): curve transform
        """
        self.tfm = tfm
        self.clean_name = self.tfm.split(':')[-1]

        super(HFnMesh, self).__init__(self.tfm)
        if not self.shp:
            raise RuntimeError(tfm)
        _dag_path = HDagPath(self.shp.node)
        om.MFnMesh.__init__(self, _dag_path)
        if not self.shp.typeName == 'mesh':
            raise RuntimeError(tfm)

        self.vtx = IndexedAttrGetter(node=self, attr='vtx')
        self.edge = IndexedAttrGetter(node=self, attr='e')
        self.map = IndexedAttrGetter(node=self, attr='map')

    def difference(self, other):
        """Apply boolean difference with another mesh.

        Args:
            other (HFnMesh): other mesh

        Returns:
            (HFnMesh): new mesh
        """
        from maya_psyhive import open_maya as hom
        _name = str(self)
        _result = hom.CMDS.polyCBoolOp(
            self, other, operation=2, constructionHistory=False)
        _result = _result.rename(get_unique(_name))
        return self.__class__(str(_result))

    def get_edges(self):
        """Get list of edges in this mesh.

        Returns:
            (str list): edges
        """
        _n_edges = cmds.polyEvaluate(self, edge=True)
        return [self.edge[_idx] for _idx in range(_n_edges)]

    def get_uvs(self, class_=None):
        """Get list of uvs in this mesh (map).

        Args:
            class_ (type): cast uv to given type

        Returns:
            (str list): uvs
        """
        _n_uvs = cmds.polyEvaluate(self, uv=True)
        _uvs = [self.map[_idx] for _idx in range(_n_uvs)]
        if class_:
            _uvs = [class_(_uv) for _uv in _uvs]
        return _uvs

    def get_vtxs(self):
        """Get list of vertices in this mesh.

        Returns:
            (str list): vertices
        """
        _n_vtxs = cmds.polyEvaluate(self, vertex=True)
        return [self.vtx[_idx] for _idx in range(_n_vtxs)]

    def intersection(self, other):
        """Get intersection between this mesh and another object.

        Args:
            other (any): object to intersect

        Returns:
            (any): intersect (depends on object provided)
        """
        from maya_psyhive import open_maya as hom
        if isinstance(other, hom.HVRay):
            return _mesh_to_ray_intersection(mesh=self, ray=other)
        else:
            raise ValueError(other)

    @property
    def make(self):
        """Find make node for this mesh (if any).

        TODO: extend this for other mesh types.

        Returns:
            (HFnDependencyNode): make node
        """
        return get_single(self.shp.find_connected(type_='polyPlane'),
                          catch=True)

    def triangulate(self):
        """Triangulate this mesh."""
        cmds.polyTriangulate(self, constructionHistory=False)


def _mesh_to_ray_intersection(
        ray, mesh, both_dirs=True, clean_up=True, above_only=True):
    """Calculate ray/mesh intersections.

    Args:
        ray (HVRay): ray object
        mesh (HFnMehs): mesh object
        both_dirs (bool): check intersections in both directions (ie. if
            this if false then intersections coming out of faces will not
            be flagged)
        clean_up (bool): remove duplicate points - these can occur if a ray
        intersects an the edge between two faces
        above_only (bool): remove points behind the ray's start point

    Returns:
        (HPoint list): list of points
    """
    from maya_psyhive import open_maya as hom

    _ray_src = om.MFloatPoint(*ray.pnt.to_tuple())
    _ray_dir = om.MFloatVector(*ray.vec.to_tuple())
    _space = om.MSpace.kWorld
    _max_param = 999999

    _result = mesh.allIntersections(
        _ray_src,
        _ray_dir,
        _space,
        _max_param,
        both_dirs,
    )

    # Convert to HPoints
    _pts = []
    for _item in _result[0]:
        _pt = hom.HPoint(_item)
        _pts.append(_pt)

    lprint('FOUND {:d} PTS'.format(len(_pts)), _pts, verbose=0)

    # Remove duplicate points
    if clean_up:
        _clean_pts = []
        while _pts:
            _clean_pts.append(_pts.pop())
            for _pt in copy.copy(_pts):
                for _clean_pt in _clean_pts:
                    if not (_pt-_clean_pt).length():
                        _pts.remove(_pt)
        _pts = _clean_pts

    # Remove points behind the ray's start point
    if above_only:
        _above_pts = []
        _plane = ray.to_plane()
        for _pt in _pts:
            _dist = _plane.distanceToPoint(hom.HVector(_pt), signed=True)
            if _dist > 0.0001:
                _above_pts.append(_pt)
        _pts = _above_pts

    return _pts
