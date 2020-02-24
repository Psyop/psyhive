"""Tools for frasier_38732V project."""

import os
import shutil
import sys

from maya import cmds

from psyhive import icons, py_gui, host, refresh
from psyhive.utils import store_result, File, nice_size

from maya_psyhive import ref, ui
from maya_psyhive.tools import fkik_switcher
from maya_psyhive.shows import vampirebloodline

ICON = icons.EMOJI.find('Brain')
_ROOT = ('P:/projects/frasier_38732V/code/primary/addons/general/'
         'frasier/_ToolsPsy')
_PY_ROOT = _ROOT+'/release/maya/v2018/hsl/python'
_INGEST_ROOT = 'P:/projects/frasier_38732V/production/vendor_in/Motion Burner'
_MOTIONBURNER_RIG = ('P:/projects/frasier_38732V/production/vendor_in/'
                     'Motion Burner/2020-02-11-BodyRig/SK_Tier1_Male_CR.ma')
_KEALEYE_TOOLS_ROOT = 'P:/projects/frasier_38732V/production/kealeye_tools'


py_gui.set_section("Ingestion tools")


def _ingest_ma(ma_, load_ma=True, force=False, apply_mapping=True,
               legs_to_ik=False, save=True):
    """Ingest ma file from vendor in to the pipeline, ie. create work.

    Args:
        ma_ (FrasierVendorMa): source file
        load_ma (bool): load ma file (disable for debugging)
        force (bool): lose unsaved changes without warning
        apply_mapping (bool): update rig to HSL rig
        legs_to_ik (bool): update legs from fk to ik
        save (bool): save ma file is psyop work file
    """
    if ma_ and load_ma:
        print 'INGEST', ma_
        _load_vendor_ma(ma_.path, force=force)
        ma_.get_range(force=True)  # Cache range

    if apply_mapping:
        _apply_kealeye_rig_mapping()

    if legs_to_ik:
        _update_legs_to_ik()

    if save:
        _work = ma_.get_work()
        print ' - WORK', _work
        print ' - RANGE', ma_.get_range()
        _work.save(comment='Copied from '+ma_.path)
        _work.set_vendor_file(ma_.path)
        _work.has_ik_legs()  # Store cache
        if legs_to_ik:
            assert _work.has_ik_legs()


def _load_vendor_ma(path, force=False, lazy=False):
    """Load vendor ma file.

    The file is loaded and then the bad rig reference is updated.

    Args:
        path (str): vendor ma file
        force (bool): lose unsaved changes with no warning
        lazy (bool): don't open scene if it's already open
    """

    # Load scene
    if not lazy or host.cur_scene() != path:

        if not force:
            host.handle_unsaved_changes()

        # Load the scene
        try:
            cmds.file(path, open=True, prompt=False, force=True)
        except RuntimeError as _exc:
            if "has no '.ai_translator' attribute" in _exc.message:
                pass
            else:
                print '######################'
                print _exc.message
                print '######################'
                raise RuntimeError('Error on loading scene')

        assert host.get_fps() == 30

    # Update rig
    _ref = ref.find_ref()
    if not _ref.path == _MOTIONBURNER_RIG:
        _ref.swap_to(_MOTIONBURNER_RIG)


@store_result
def _install_mocap_tools():
    """Install Sean Kealeye MocapTools module."""
    refresh.add_sys_path(_KEALEYE_TOOLS_ROOT)
    assert os.path.exists(_KEALEYE_TOOLS_ROOT)
    assert os.path.exists(_KEALEYE_TOOLS_ROOT+'/MocapTools')
    import MocapTools
    print 'INSTALLED MocapTools MODULE', MocapTools


def _apply_kealeye_rig_mapping():
    """Apply rig mapping from Sean Kealeye MocapTools.

    This brings in the HSL rig, binds it to the MotionBurner skeleton,
    then bakes the anim. The MotionBurner rig is left in the scene
    for comparison but it is placed in a group and hidden.
    """
    _install_mocap_tools()
    from MocapTools.Scripts import PsyopMocapTools

    # Apply kealeye bake
    PsyopMocapTools.mocapSetupTools().bakeControlRigScene(incFace=True)

    # Clean up scene
    cmds.currentTime(1)  # Update anim
    cmds.select([
        _node for _node in cmds.ls('SK_Tier1_Male_CR:*', long=True, dag=True)
        if _node.count('|') == 1])
    _grp = cmds.group(name='CaptureRig_GRP')
    cmds.setAttr(_grp+'.visibility', False)
    _editor = ui.get_active_model_panel()
    cmds.modelEditor(_editor, edit=True, nurbsCurves=True)


def _update_legs_to_ik():
    """Update legs from fk t ik in current scene."""
    for _ctrl in ['SK_Tier1_Male:IKLeg_L', 'SK_Tier1_Male:IKLeg_R']:
        cmds.select(_ctrl)
        _system = fkik_switcher.get_selected_system(
            class_=vampirebloodline.VampireFkIkSystem)
        _system.exec_switch_and_key_over_range(
            switch_mode='fk_to_ik', switch_key=False, selection=False)


@py_gui.install_gui(
    browser={'ma_': py_gui.BrowserLauncher(default_dir=_INGEST_ROOT)},
    label='Prepare MotionBurner ma file')
def prepare_motionburner_ma_file(ma_, use_hsl_rig=True, legs_to_ik=False):
    """Prepare MotionBurner ma file from vendor in.

    This opens the scene and updates the broken rig reference to the one on
    our file system.

    Args:
        ma_ (str): path to ma file to load
        use_hsl_rig (bool): update the rig to HSL rig
        legs_to_ik (bool): update legs from fk to ik for animation (slow)
    """
    if ma_:
        _load_vendor_ma(ma_)
    _ingest_ma(ma_=None, legs_to_ik=legs_to_ik, apply_mapping=use_hsl_rig,
               save=False)


def _export_hsl_fbx_from_cur_scene(fbx):
    """Export HSL format fbx from the current scene.

    This uses the MocapTools library.

    Args:
        fbx (str): path to export to
    """
    cmds.loadPlugin('fbxmaya', quiet=True)
    _install_mocap_tools()
    from MocapTools.Scripts import PsyopMocapTools

    _tmp_fbx = File('{}/MocapTools/Anim/Export/{}_SK_Tier1_Male.fbx'.format(
        _KEALEYE_TOOLS_ROOT, File(host.cur_scene()).basename))
    print ' - TMP FBX', _tmp_fbx.path

    _setup = PsyopMocapTools.mocapSetupTools()
    _tmp_fbx.delete(force=True)
    assert not _tmp_fbx.exists()
    _setup.exportAnim(PsyopMocapTools.config.animFBX)
    assert _tmp_fbx.exists()

    # Move from tmp dir
    _fbx = File(fbx)
    _fbx.test_dir()
    shutil.move(_tmp_fbx.path, _fbx.path)
    print ' - SAVED FBX', nice_size(_fbx.path), _fbx.path


@py_gui.install_gui(
    browser={'fbx': py_gui.BrowserLauncher(
        default_dir='P:/projects/frasier_38732V')},
    label='Export HSL fbx')
def export_hsl_fbx(fbx=''):
    """Export an HSL format fbx.

    Args:
        fbx (str): path to export to
    """
    _export_hsl_fbx_from_cur_scene(fbx)


py_gui.set_section("Animation")


@py_gui.install_gui(label='Launch FK/IK switcher')
def launch_fkik_switcher():
    """Launch FK/IK switcher interface for HSL rig."""
    return fkik_switcher.launch_interface(
        system_=vampirebloodline.VampireFkIkSystem)


py_gui.set_section("HSL Tools")


@py_gui.install_gui(label='Install HSL tools')
def install_hsl_tools():
    """Install Hardsuit-Labs tools."""
    os.environ['MAYA_START_MELSCRIPT'] = _ROOT+(
        '/release/maya/v2018/hsl/MEL/launch_scripts/'
        'maya_2018_startup_frasier.mel')

    _3rd_party_root = _ROOT+'/release/maya/v2018/3rdparty/python'
    for _root in [_PY_ROOT, _3rd_party_root]:
        while _root in sys.path:
            sys.path.remove(_root)
        sys.path.insert(0, _root)

    import art_tools
    art_tools.startup()


@py_gui.install_gui(label='Launch HSL Anim Exporter')
def launch_hsl_anim_exporter():
    """Launch hsl anim exporter."""
    install_hsl_tools()
    from art_tools.gui.qt.dialog import animation_exporter_2
    animation_exporter_2.open_tool()
