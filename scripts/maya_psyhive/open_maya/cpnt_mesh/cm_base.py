"""Tools for managing the base class of mesh components."""

from maya import cmds

from maya_psyhive.open_maya.cpnt_mesh import cm_utils


class CpntBase(object):
    """Base class for any mesh component (face/edges/vtx)."""

    def __init__(self, attr):
        """Constructor.

        Args:
            attr (str): component attr (eg. "mesh.f[12]")
        """
        self.attr = attr

    def delete(self):
        """Delete this component."""
        cmds.delete(self)

    def to_edges(self):
        """Map component to edges.

        Returns:
            (CpntEdge list): list of edges
        """
        from maya_psyhive.open_maya.cpnt_mesh import cm_edge
        return [cm_edge.CpntEdge(_edge)
                for _edge in cm_utils.to_edges(str(self))]

    def to_faces(self):
        """Map component to faces.

        Returns:
            (CpntFace list): list of faces
        """
        from maya_psyhive.open_maya.cpnt_mesh import cm_face
        return [cm_face.CpntFace(_face)
                for _face in cm_utils.to_faces(str(self))]

    def to_vtxs(self):
        """Map component to vertices.

        Returns:
            (CpntVtx list): list of vertices
        """
        from maya_psyhive.open_maya.cpnt_mesh import cm_vtx
        return [cm_vtx.CpntVtx(_vtx)
                for _vtx in cm_utils.to_vtxs(str(self))]

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __str__(self):
        return self.attr

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__.strip('_'), self.attr)
