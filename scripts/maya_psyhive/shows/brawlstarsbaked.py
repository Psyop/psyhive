"""Toolkit for brawl stars baked project."""

from maya import cmds

from psyhive import icons, py_gui
from psyhive.utils import get_single
from maya_psyhive import open_maya as hom

ICON = icons.EMOJI.find("Star")
LABEL = "Brawlstars Baked"
BUTTON_LABEL = 'brawl\nstars'


py_gui.set_section('Mesh XRay Plugin')


@py_gui.install_gui(label='Apply MeshXRayer to selected mesh')
def apply_mesh_xrayer_to_sel():
    """Apply mesh xrayer to selected mesh."""

    _mesh = hom.get_selected(class_=hom.HFnMesh)
    print 'SELECTION', _mesh

    # Apply triangulation if needed
    _trianglate_required = False
    for _poly_id in range(_mesh.numPolygons):
        _vtx_ids = _mesh.getPolygonVertices(_poly_id)
        if len(_vtx_ids) > 3:
            _trianglate_required = True
            break
    if _trianglate_required:
        cmds.polyTriangulate()

    # Create mesh xrayer
    cmds.loadPlugin('mesh_xrayer', quiet=True)
    _loc_s = hom.CMDS.createNode('MeshXRayer')
    _loc = _loc_s.get_parent()
    cmds.parent(_loc, _mesh, relative=True)
    cmds.connectAttr(_mesh.plugs('worldMesh[0]'), _loc.plugs('in_mesh'))
    cmds.select(_loc_s)


@py_gui.install_gui(label='Remove MeshXRayer from selected mesh')
def remove_mesh_xrayer_from_sel():
    """Remove mesh xrayer to selected mesh."""
    _mesh = hom.get_selected(class_=hom.HFnMesh)
    print 'SELECTION', _mesh
    _mxray = get_single(_mesh.shp.list_outgoing(type='MeshXRayer'))
    print 'MESH XRAY', _mxray
    _tri = get_single(_mesh.shp.list_incoming(type='polyTriangulate'),
                      catch=True)
    print 'TRI', _tri
    cmds.delete([_node for _node in (_mxray, _tri) if _node])
