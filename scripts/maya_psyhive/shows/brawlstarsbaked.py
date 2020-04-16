"""Toolkit for brawl stars baked project."""

import tempfile

from maya import cmds

import psylaunch

from psyhive import icons, qt, py_gui, tk2, host
from psyhive.utils import (
    get_plural, Seq, get_single, lprint, check_heart, Dir, File,
    abs_path)

from maya_psyhive import open_maya as hom, ref
from maya_psyhive.utils import mel_, restore_sel

ICON = icons.EMOJI.find("Star")
LABEL = "Brawlstars Baked"
BUTTON_LABEL = 'brawl\nstars'
_SEQS = [_seq.name for _seq in tk2.obtain_sequences()]
_TMP_DIR = '{}/tbm_tmp/'.format(tempfile.gettempdir())
_FACE_MATTES_NK = ('P:/projects/brawlstarsbaked_37322B/reference/documents/'
                   'face_mattes/face_blur_setup_v003.nk')


py_gui.set_section('Beast Makers Plugin')


def _get_rig(tbm, verbose=0):
    """Get rig from the given TBM node.

    Args:
        tbm (str): TBM node to read
        verbose (int): print process data

    Returns:
        (FileRef): rig
    """
    lprint('GET RIG', tbm, verbose=verbose)

    _shds = sum([
        tbm.find_connected(type_=_type)
        for _type in ('lambert', 'blinn', 'phong')], [])
    _shd = get_single(_shds, catch=True)
    if not _shd:
        raise RuntimeError("Couldn't determine rig for {}".format(tbm))
    lprint(' - SHADER', _shd, verbose=verbose)

    _ses = _shd.plug('outColor').list_outgoing(type='shadingEngine')
    _se = get_single(_ses, catch=True)
    if not _se:
        print ' - SHADING ENGINES', _ses
        raise RuntimeError(
            "Found {:d} shading engine{} attached to {}".format(
                len(_ses), get_plural(_ses), _shd))
    lprint(' - SHADING ENGINE', _se, verbose=verbose)

    _nodes = [_node for _node in hom.CMDS.sets(_se, query=True)
              if not _node.namespace == tbm.namespace]

    if not _nodes:
        raise RuntimeError("No rig found for {}".format(tbm))

    _namespace = _nodes[0].namespace
    _ref = ref.find_ref(namespace=_namespace)
    lprint(' - REF', _ref, verbose=verbose)

    return _ref


def _get_render(tbm, pass_):
    """Get render for the given pass/tbm node.

    Args:
        tbm (HFnDependencyNode): beast makers node
        pass_ (str): pass name

    Returns:
        (TTOutputFileSeq): render
    """
    _cur_work = tk2.cur_work()
    _tag = 'srgb' if pass_ == 'Diffuse' else 'data'
    return _cur_work.map_to(
        tk2.TTOutputFileSeq, output_type='faceRender',
        format=str(tbm.clean_name), extension='png',
        output_name=tbm.rig.namespace, channel=pass_, eye=_tag)


def _prepare_tbms(tbms, force=False):
    """Prepare beast maker nodes for export.

    This stores render data on the nodes and checks output paths
    are clear for rendering.

    Args:
        tbms (HFnDependencyNode list): list of nodes to export
        force (bool): remove existing outputs without confirmation
    """
    Dir(_TMP_DIR).delete(force=True)

    for _tbm in tbms:

        print _tbm
        _tbm.rig = _get_rig(_tbm)
        _tbm.face_rig = ref.find_ref(_tbm.namespace)
        _tbm.face_ctrl = _tbm.face_rig.get_node('face_Placer_Ctrl')
        _tbm.plug('fileFormat').set_enum('png')
        _tbm.plug('recordSizeX').set_val(2048)
        _tbm.plug('recordSizeY').set_val(2048)
        _tbm.plug('recordColorPrecision').set_enum('16 bit integer')

        _tbm.renders = {}
        _tbm.tmp_seqs = {}

        for _pass in ['Bump', 'Alpha']:
            _get_render(tbm=_tbm, pass_=_pass).delete(force=force)

        # Set up matte attr + remove any anim (kcassidy)
        _tbm.matte_attr = _tbm.face_ctrl.plug('matte')
        _tbm.matte_attr.break_connections()

        # Set up passes
        _tbm.passes = _tbm.matte_attr.list_enum()
        for _pass in _tbm.passes:

            # Set up render
            _render = _get_render(tbm=_tbm, pass_=_pass)
            _render.delete(force=force)
            _render.test_dir()
            _tbm.renders[_pass] = _render
            print ' - RENDER', _render

            # Set up tmp seq
            _tmp_seq = Seq('{}/{}/{}/{}_color.%04d.png'.format(
                _TMP_DIR, _tbm.rig.namespace, _tbm.clean_name, _pass))
            _tmp_seq.test_dir()
            _tbm.tmp_seqs[_pass] = _tmp_seq
            print ' - TMP', _tmp_seq

    print


def _render_tbms(tbms, start, end):
    """Render beast maker nodes.

    The list of passes is defined by the face_Placer_Ctrl.matt enum. Each
    pass must be rendered separately.

    Args:
        tbms (HFnDependencyNode list): nodes to export
        start (int): start frame
        end (int): end frame
    """

    # Disable unused nodes
    for _tbm in hom.CMDS.ls(type='TBM_2DRenderer'):
        if _tbm not in tbms:
            _tbm.plug('record').set_val(False)

    # Render passes
    _pass_count = max([len(_tbm.renders) for _tbm in tbms])
    for _idx in qt.progress_bar(
            range(_pass_count), 'Rendering {:d} pass{}', plural='es'):

        # Prepare tbm nodes
        _to_move = []
        for _tbm in tbms:
            _passes = sorted(_tbm.renders)
            if _idx < len(_tbm.renders):
                _pass = _passes[_idx]
                _tbm.plug('directory').set_val(_tbm.tmp_seqs[_pass].dir)
                _tbm.plug('fileName').set_val(_pass)
                _tbm.plug('record').set_val(True)
                _tbm.matte_attr.set_enum(_pass)
                _to_move.append((
                    _tbm, _tbm.tmp_seqs[_pass], _tbm.renders[_pass]))
            else:
                _tbm.plug('record').set_val(False)

        # Render
        mel_("TBM_2DRecord -fs {start:d} -fe {end:d}".format(
            start=start, end=end))

        # Move images to pipeline
        for _tbm, _tmp_seq, _render in _to_move:
            _rng = _tmp_seq.find_range()
            print 'RNG', _rng
            if _rng != (start, end):
                raise RuntimeError(
                    'TBM node {} failed to render - this could be due to '
                    'disabled TBM nodes in the scene'.format(_tbm))
            _tmp_seq.move(_render)

    # Revert to diffuse
    for _tbm in tbms:
        _tbm.matte_attr.set_enum('Diffuse')


def _comp_tbm_renders(tbms, start, end):
    """Comp beast maker renders.

    This generates the alpha and bump passes by passing the RGB render through
    a nk file.

    Args:
        tbms (HFnDependencyNode list): nodes to export
        start (int): start frame
        end (int): end frame
    """
    _tmp_py = abs_path('{}/process_mattes.py'.format(_TMP_DIR))
    print _tmp_py

    _py = '\n'.join([
        'import nuke',
        '',
        'nuke.scriptOpen("{nk}")',
        '',
        '_read_rgb = nuke.toNode("ReadRGB")',
        '_write_bump = nuke.toNode("WriteBump")',
        '_write_alpha = nuke.toNode("WriteAlpha")',
        '',
    ]).format(nk=_FACE_MATTES_NK)

    for _tbm in tbms:
        _bump = _get_render(tbm=_tbm, pass_='Bump')
        _alpha = _get_render(tbm=_tbm, pass_='Alpha')
        _rgb = _get_render(tbm=_tbm, pass_='RGB')
        _py += '\n'.join([
            '',
            '# Process {tbm}',
            '_read_rgb["file"].setValue("{matte_raw}")',
            '_read_rgb["first"].setValue({start})',
            '_read_rgb["last"].setValue({end})',
            '_write_bump["file"].setValue("{bump}")',
            'nuke.render(_write_bump, {start}, {end})',
            '_write_alpha["file"].setValue("{alpha}")',
            'nuke.render(_write_alpha, {start}, {end})',
        ]).format(
            tbm=_tbm, bump=_bump.path, alpha=_alpha.path, start=start,
            end=end, matte_raw=_rgb.path)

    # print _py
    # print
    File(_tmp_py).write_text(_py, force=True)

    print 'launch nuke -- -t "{}"'.format(_tmp_py)
    psylaunch.launch_app('nuke', args=['-t', _tmp_py])


@py_gui.install_gui(choices={'which': ['All', 'Select']})
def render_tbm_nodes(which='All', force=False):
    """Render TBM_2DRender nodes in the current scene.

    Args:
        which (str): which nodes to render:
            all - render all nodes in the scene
            select - select which nodes to render from a list
        force (bool): overwrite existing renders without confirmation
    """
    _cur_work = tk2.cur_work()
    _start, _end = [int(_val) for _val in host.t_range()]

    # Get list of tmb nodes to render
    _tbms = hom.CMDS.ls(type='TBM_2DRenderer')
    if which == 'Select' and len(_tbms) > 1:
        _tbms = qt.multi_select(
            _tbms, 'Which TBM nodes to render?', default=_tbms)

    _prepare_tbms(tbms=_tbms, force=force)
    _render_tbms(tbms=_tbms, start=_start, end=_end)
    _comp_tbm_renders(tbms=_tbms, start=_start, end=_end)


py_gui.set_section('Face Rigs')


@restore_sel
def connect_faces_to_rigs():
    """Connect all face rigs to their corresponding rigs."""
    _chars = [
        'barley', 'bibi', 'crow', 'dynamike', 'elprimo', 'emz', 'jessie',
        'mortis', 'nita', 'piper', 'poco', 'rico']

    _refs = ref.find_refs()

    for _face_rig in _refs:

        # Match to a char
        _char = None
        for _o_char in _chars:
            if _o_char in _face_rig.namespace:
                _char = _o_char
        if not _char:
            continue

        # Check show name attr exists
        _ctrl = '{}:face_Placer_Ctrl'.format(_face_rig.namespace)
        if not cmds.objExists(_ctrl):
            continue

        print 'CONNECTING FACE RIG', _face_rig
        _shader = '{}:TBM2Dskin__Shd'.format(_face_rig.namespace)
        print ' - SHADER', _shader
        _geo_name = cmds.getAttr(
            '{}:face_Placer_Ctrl.geo'.format(_face_rig.namespace))
        print ' - GEO NAME', _geo_name
        _char_name = cmds.getAttr(
            '{}:face_Placer_Ctrl.character'.format(_face_rig.namespace))
        print ' - CHAR NAME', _char_name

        _rig = get_single([
            _ref for _ref in _refs
            if _face_rig.namespace.startswith(_ref.namespace) and
            not _ref == _face_rig])
        print ' - RIG', _rig
        _geo = _rig.get_node(_geo_name)
        print ' - GEO', _geo

        cmds.select(_geo)
        cmds.hyperShade(assign=_shader)


def unload_selected_face_rigs():
    """Unload selected rigs."""
    for _ref in ref.get_selected(multi=True):
        print 'REF', _ref
        for _tbm in _ref.find_nodes(type_='TBM_2DRenderer'):
            print ' - TBM', _tbm
            for _plug in _tbm.plug('shapes').list_incoming(plugs=True):
                _conns = [
                    _conn for _conn in hom.read_outgoing(_plug, class_=str)
                    if _conn[1].startswith(str(_tbm))]
                if not _conns:
                    continue
                _src, _dest = get_single(_conns)
                cmds.disconnectAttr(_src, _dest)
        _ref.unload()


@py_gui.hide_from_gui
def load_selected_rigs():
    """Load selected face rigs."""
    for _ref in ref.get_selected(multi=True):
        print 'REF', _ref

        if not _ref.is_loaded():
            _ref.load()

        for _edit in qt.progress_bar(cmds.referenceQuery(
                _ref.ref_node, editStrings=True, editCommand="disconnectAttr",
                showDagPath=True)):
            if 'TBM_2DRenderer.shapes' not in _edit:
                continue
            # print _edit
            _, _src, _trg = _edit.split()
            cmds.referenceEdit(
                _trg, removeEdits=True, failedEdits=True, successfulEdits=True,
                editCommand="disconnectAttr")


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
