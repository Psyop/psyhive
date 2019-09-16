"""Tools for clash short file project."""

from maya import cmds

from psyhive import host, py_gui
from psyhive.utils import File, get_single
from maya_psyhive import ui
from maya_psyhive import open_maya as hom

LABEL = "Clash Short"


def _get_scene_name():
    """Get current scene name hud text.

    Returns:
        (str): scene name hud text
    """
    _cur_scene = host.cur_scene()
    return 'file: {}'.format(
        File(_cur_scene).filename if _cur_scene else '')


def _get_frame():
    """Get current frame hud text.

    Returns:
        (str): current frame hud text
    """
    return 'frame: {:d}'.format(int(cmds.currentTime(query=True)))


def _get_cam_focal():
    """Get cam focal hud text.

    Returns:
        (str): cam focal hud text
    """
    _model = ui.get_active_model_panel()
    _cam = hom.HFnCamera(cmds.modelPanel(_model, query=True, camera=True))
    return 'focal: {:.02f}'.format(_cam.shp.plug('focalLength').get_val())


def _get_hud_data():
    """Get clash short hud data.

    Returns:
        (tuple list): list of hud data
    """
    return [
        ('PsyHudFilename', (2, 0), _get_scene_name, {
            'conditionChange': 'postSceneCallbacks'}),
        ('PsyHudFrame', (5, 0), _get_frame, {
            'attachToRefresh': True}),
        ('PsyHudFocal', (9, 0), _get_cam_focal, {
            'attachToRefresh': True}),
    ]


py_gui.set_section('HUD', collapse=False)


@py_gui.install_gui()
def install_hud():
    """Install clash short hud."""
    uninstall_hud()
    for _name, _pos, _cmd, _kwargs in _get_hud_data():
        cmds.headsUpDisplay(removePosition=_pos)
        cmds.headsUpDisplay(
            _name, section=_pos[0], block=_pos[1], blockSize='large',
            labelFontSize='large', command=_cmd, **_kwargs)


@py_gui.install_gui()
def uninstall_hud():
    """Remove clash short hud."""
    for _name, _, _, _ in _get_hud_data():
        if cmds.headsUpDisplay(_name, query=True, exists=True):
            cmds.headsUpDisplay(_name, remove=True)


py_gui.set_section('VDB', collapse=False)


def _find_sg(vdb):
    """Find shading group of the given vdb.

    Args:
        vdb (HFnDependencyNode): vdb to read

    Returns:
        (HFnDependencyNode): shading group
    """
    return get_single([
        _set for _set in hom.CMDS.ls(type='objectSet')
        if vdb in (cmds.sets(_set, query=True) or [])])


@py_gui.install_gui()
def fix_vdb_shaders():
    """Fix shaders on vdb nodes.

    In some cases, having a surface shader applied to a vdb node seems
    to make maya seg fault when the viewport draws it.

    To fix the scene, pause the viewport, open the scene, run this fix
    and then you should be able to unpause the viewport without maya
    erroring.
    """
    for _vdb in hom.CMDS.ls(type='aiVolume'):
        _sg = _find_sg(_vdb)
        print _vdb, _sg
        _sg.plug('surfaceShader').break_connections()
        assert not _sg.plug('surfaceShader').list_connections()


py_gui.set_section('Dev')


def fix_larry_scale():
    """Fix larry scale."""
    _mult = 1.05
    _namespace = 'peter'
    _ctrls = [
        'Lf_legIk_Ctrl',
        'Rt_legIk_Ctrl',
        'Rt_armIk_Ctrl',
        'Rt_armIk_Ctrl',
        'cog_Ctrl',
        'mover_Ctrl',
    ]
    _attrs = ['{}:{}.translate'.format(_namespace, _ctrl) for _ctrl in _ctrls]
    for _attr in _attrs:
        _val = cmds.getAttr(_attr)[0]
        _new_val = [_item*_mult for _item in _val]
        cmds.setAttr(_attr, *_new_val)
