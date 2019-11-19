"""Tools for managing component meshes."""

from maya_psyhive.open_maya import mesh
from maya_psyhive.open_maya.cpnt_mesh import (
    cm_vtx, cm_edge, cm_face, cm_utils, cm_uv)


class CpntMesh(mesh.HFnMesh):
    """Mesh with access to components (face/edges/vtx)."""

    def to_edges(self):
        """Get mesh edges.

        Returns:
            (CpntEdge list): list of edges
        """
        return [cm_edge.CpntEdge(_edge) for _edge in cm_utils.to_edges(self)]

    def to_face(self, idx):
        """Get a face of this mesh.

        Args:
            idx (int): face index

        Returns:
            (CpntFace): face
        """
        return cm_face.CpntFace('{}.f[{:d}]'.format(self, idx))

    def to_faces(self):
        """Get mesh faces.

        Returns:
            (CpntFace list): list of faces
        """
        return [cm_face.CpntFace(_face) for _face in cm_utils.to_faces(self)]

    def to_vtxs(self):
        """Get mesh vertices.

        Returns:
            (CpntVtx list): list of vertices
        """
        return [cm_vtx.CpntVtx(_vtx) for _vtx in cm_utils.to_vtxs(self)]

    def to_uvs(self):
        """Get mesh vertices.

        Returns:
            (CpntVtx list): list of vertices
        """
        return [cm_uv.CpntUV(_vtx) for _vtx in cm_utils.to_uvs(self)]
