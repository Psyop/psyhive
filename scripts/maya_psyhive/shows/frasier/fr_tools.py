"""Tools for managing mocap ingestion on fraiser."""

import os
import shutil

from maya import cmds

from psyhive import host, refresh
from psyhive.utils import store_result, File, nice_size

from maya_psyhive.utils import pause_viewports_on_exec

KEALEYE_TOOLS_ROOT = 'P:/projects/frasier_38732V/production/kealeye_tools'


@store_result
def install_mocap_tools():
    """Install Sean Kealeye MocapTools module."""
    refresh.add_sys_path(KEALEYE_TOOLS_ROOT)
    assert os.path.exists(KEALEYE_TOOLS_ROOT)
    assert os.path.exists(KEALEYE_TOOLS_ROOT+'/MocapTools')
    import MocapTools
    print 'INSTALLED MocapTools MODULE', MocapTools


@pause_viewports_on_exec
def export_hsl_fbx_from_cur_scene(fbx, force=False):
    """Export HSL format fbx from the current scene.

    This uses the MocapTools library.

    Args:
        fbx (str): path to export to
        force (bool): overwrite existing files without confirmation
    """
    cmds.loadPlugin('fbxmaya', quiet=True)
    install_mocap_tools()
    from MocapTools.Scripts import PsyopMocapTools

    _fbx = File(fbx)
    if _fbx.exists():
        _fbx.delete(wording='Overwrite', force=force)

    _tmp_fbx = File('{}/MocapTools/Anim/Export/{}_SK_Tier1_Male.fbx'.format(
        KEALEYE_TOOLS_ROOT, File(host.cur_scene()).basename))
    print ' - TMP FBX', _tmp_fbx.path

    _setup = PsyopMocapTools.mocapSetupTools()
    _tmp_fbx.delete(force=True)
    assert not _tmp_fbx.exists()
    _setup.exportAnim(PsyopMocapTools.config.animFBX)
    assert _tmp_fbx.exists()

    # Move from tmp dir
    _fbx.test_dir()
    shutil.move(_tmp_fbx.path, _fbx.path)
    print ' - SAVED FBX', nice_size(_fbx.path), _fbx.path
