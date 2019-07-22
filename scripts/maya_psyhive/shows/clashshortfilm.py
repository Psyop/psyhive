"""Tools for clash short file project."""

from maya import cmds

from psyhive import host, py_gui
from psyhive.utils import File
from maya_psyhive import ui
from maya_psyhive import open_maya as hom


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