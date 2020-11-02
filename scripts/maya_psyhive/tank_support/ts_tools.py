"""General tank support tools."""

from maya import cmds

from psyhive.tools import catch_error
from psyhive.utils import lprint
from maya_psyhive import open_maya as hom


@catch_error
def read_mesh_data(verbose=0):
    """Read mesh data from current scene.

    Args:
        verbose (int): print process data

    Returns:
        (dict): mesh data
    """

    # Get list of meshes
    if cmds.objExists('bakeSet'):
        _meshes = []
        for _node in (cmds.sets('bakeSet', query=True) or []):
            try:
                _meshes.append(hom.HFnMesh(_node))
            except RuntimeError:
                continue
    else:
        _meshes = hom.find_nodes(class_=hom.HFnMesh)

    # Read mesh data
    _data = {}
    for _mesh in _meshes:

        if _mesh.isFromReferencedFile:
            continue

        _uv_sets = [str(_set) for _set in _mesh.getUVSetNames()]

        lprint('MESH', _mesh, _mesh.shp, _mesh.shp.typeName, verbose=verbose)
        lprint(' - NUM VTXS', _mesh.numVertices, verbose=verbose)
        lprint(' - UV SETS', _mesh.numUVSets, _uv_sets, verbose=verbose)

        _mesh_data = {}
        _mesh_data['uv_sets'] = _uv_sets
        _mesh_data['vtx_count'] = _mesh.numVertices
        _mesh_data['poly_count'] = _mesh.numPolygons
        _data[str(_mesh)] = _mesh_data

    return _data
