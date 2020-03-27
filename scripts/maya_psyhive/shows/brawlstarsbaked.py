"""Toolkit for brawl stars baked project."""

from maya import cmds, mel

from psyhive import icons, qt, py_gui, tk2
from psyhive.utils import get_plural, Seq, get_single, lprint, check_heart

from maya_psyhive import open_maya as hom, ref

ICON = icons.EMOJI.find("Star")
LABEL = "Brawlstars Baked"
BUTTON_LABEL = 'brawl\nstars'
_SEQS = [_seq.name for _seq in tk2.obtain_sequences()]


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


py_gui.set_section('Previs Cleanup')


def _get_correct_namespace(ref_, used=()):
    """Get target namespace for the given reference.

    If it is the first instance, just use the asset name - for subsequent
    instances add _ index (eg. archer, archer_2).

    Args:
        ref_ (FileRef): reference to check
        used (tuple): list of namespaces to avoid

    Returns:
        (str): target namespace
    """
    _asset = tk2.TTOutputName(ref_.path)

    _ns = _asset.asset
    _count = 1
    while (
            _ns in used or
            _ns in [_ref.namespace for _ref in ref.find_refs()] or
            cmds.namespace(exists=_ns)):
        if _ns == ref_.namespace:
            break
        check_heart()
        _count += 1
        _ns = '{}_{:d}'.format(_asset.asset, _count)
        print 'TESTING', _ns

    return _ns


def cleanup_previz_namespaces(force=False):
    """Clean up previz namespaces in the current scene.

    This updates namespaces to match asset manager style naming and updates
    the reference node names to match the new namespace.

    Args:
        force (bool): update without confirmation
    """
    _used = set()
    _rename = []
    for _ref in ref.find_refs():
        if not _ref.is_loaded():
            continue
        _namespace = _get_correct_namespace(_ref, used=_used)
        if _namespace == _ref.namespace:
            continue
        # _root
        print '{:30} {}'.format(_ref.namespace, _namespace)
        _used.add(_namespace)
        _rename.append((_ref, _namespace))

    if not force:
        qt.ok_cancel('Rename {:d} asset{}?'.format(
            len(_rename), get_plural(_rename)))
    for _ref, _namespace in qt.progress_bar(_rename):
        _ref.rename(_namespace)


def _load_and_cleanup_workfile(work):
    """Load the given workfile, clean it and version up.

    Args:
        work (TTWork): work file to update
    """
    print

    print 'WORK', work.path
    cmds.file(work.path, open=True, prompt=False, force=True)

    _errs = cmds.file(query=True, errorStatus=True)
    print ' - LOADED', _errs

    # Update refs
    _to_update = []
    for _ref in ref.find_refs():

        print _ref, _ref.path

        if not _errs and not _ref.is_loaded():
            continue

        try:
            _asset = tk2.TTOutputFile(_ref.path)
        except ValueError:
            print 'IGNORING OFF PIPELINE:', _ref
            continue
            # _asset = tk2.TTOutput(_ref.path)
        if _ref.is_loaded() and _asset.is_latest():
            continue

        print _asset
        _latest = _asset.find_latest()
        assert _latest.is_file()
        assert _latest.extension in ['ma', 'mb']
        print _latest
        _to_update.append((_ref, _latest))

    for _ref, _latest in qt.progress_bar(
            _to_update, 'Updating {:d} ref{}', stack_key='Update assets'):
        _ref.swap_to(_latest)
        print

    cleanup_previz_namespaces(force=True)

    work.find_next().save('Cleaned up namespaces')


@py_gui.install_gui(choices={'sequence': _SEQS})
def batch_cleanup_preview_assets(sequence='barleyBarPreviz'):
    """Batch cleanup preview asset namespaces.

    This will launch a popup asking you select a list of shots. Then
    for each shot it will:

        - open the latest previz work file
        - update assets to latest version
        - update asset namespaces
        - version up

    Args:
        sequence (str): sequence to get shots from
    """

    # Request shots to check
    _shots = tk2.find_shots(sequence=sequence)
    _shots = qt.multi_select(
        items=_shots, labels=[_shot.name for _shot in _shots],
        title='Select shots', msg='Select shots to clean up:')

    # Get works to update
    _works = []
    for _shot in _shots:
        print _shot
        _work = None
        for _task in ['previs', 'previz']:
            _task_work = _shot.map_to(
                tk2.TTWork, Step='previz', Task=_task, dcc='maya',
                extension='ma', version=1).find_latest()
            if _task_work:
                _work = _task_work
                break
        if not _work:
            print 'NO WORK', _shot
            continue
        assert _work.exists()
        _works.append(_work)

    for _work in qt.progress_bar(
            _works, 'Cleaning {:d} shot{}', stack_key='CleanupShots'):
        _load_and_cleanup_workfile(_work)
