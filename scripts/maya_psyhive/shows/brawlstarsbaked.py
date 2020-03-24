"""Toolkit for brawl stars baked project."""

from maya import cmds, mel
from psyhive import icons, qt, py_gui, tk2
from psyhive.utils import get_plural, Seq, get_single, lprint
from maya_psyhive import open_maya as hom, ref

ICON = icons.EMOJI.find("Star")
LABEL = "Brawlstars Baked"
BUTTON_LABEL = 'brawl\nstars'


py_gui.set_section('Beast Makers Plugin')


@py_gui.install_gui(choices={'which': ['All', 'Select']})
def render_tbm_nodes(which='All'):
    """Render TBM_2DRender nodes in the current scene.

    Args:
        which (str): which nodes to render:
            all - render all nodes in the scene
            select - select which nodes to render from a list
    """
    _cur_work = tk2.cur_work()

    _renders = []
    _tbms = hom.CMDS.ls(type='TBM_2DRenderer')
    if which == 'Select' and len(_tbms) > 1:
        _tbms = qt.multi_select(
            _tbms, 'Which TBM nodes to render?', default=_tbms)

    for _tbm in _tbms[:]:

        print _tbm

        # Read rig
        _rig = _get_rig(_tbm)
        if not _rig:
            qt.notify_warning(
                'No rig was found for {} - maybe it failed to connect.\n\n'
                'This node cannot be exported.'.format(_tbm))
            _tbms.remove(_tbm)
            continue

        # Set render path
        _render = _cur_work.map_to(
            tk2.TTOutputFileSeq, output_type='faceRender',
            format=_tbm.clean_name, extension='png',
            output_name=_rig.namespace)
        print _render.path
        _render_tmp = Seq('{}/{}_color.%04d.{}'.format(
            _render.dir, _render.basename, _render.extn))
        _render.get_frames(force=True)
        _render.test_dir()
        _render.delete(wording='replace')
        _renders.append((_render, _render_tmp))

        # Update tbm render node
        _tbm.plug('directory').set_val(_render.dir)
        _tbm.plug('fileName').set_val(_render.basename)
        _tbm.plug('fileFormat').set_enum('png')
        _tbm.plug('recordSizeX').set_val(2048)
        _tbm.plug('recordSizeY').set_val(2048)
        _tbm.plug('recordColorPrecision').set_enum('16 bit integer')

        print

    # Set record on/off on all render nodes
    for _tbm in hom.CMDS.ls(type='TBM_2DRenderer'):
        _tbm.plug('record').set_val(_tbm in _tbms)
        _tbm.plug('record').set_val(True)

    qt.ok_cancel(
        'Render {:d} TBM node{}?'.format(len(_tbms), get_plural(_tbms)),
        icon=icons.EMOJI.find('Ogre'))
    mel.eval("TBM_2DRecord")

    # Move images to correct path
    for _render, _render_tmp in _renders:
        _render_tmp.move(_render)


def _get_rig(tbm, verbose=0):
    """Get rig from the given TBM node.

    Args:
        tbm (str): TBM node to read
        verbose (int): print process data

    Returns:
        (FileRef): rig
    """
    lprint('GET RIG', tbm, verbose=verbose)

    _shd = get_single(tbm.find_connected(type_='lambert'))
    lprint(' - SHADER', _shd, verbose=verbose)

    _se = get_single(_shd.find_connected(type_='shadingEngine'))
    lprint(' - SHADING ENGINE', _se, verbose=verbose)

    _nodes = [_node for _node in hom.CMDS.sets(_se, query=True)
              if not _node.namespace == tbm.namespace]

    if not _nodes:
        return None

    _namespace = _nodes[0].namespace
    _ref = ref.find_ref(namespace=_namespace)
    lprint(' - REF', _ref, verbose=verbose)

    return _ref


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
