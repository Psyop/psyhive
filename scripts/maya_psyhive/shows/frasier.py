"""Tools for frasier_38732V project."""

import os
import sys

from maya import cmds

from psyhive import icons, py_gui, host
from psyhive.utils import CacheMissing

from maya_psyhive import ref, ui
from maya_psyhive.tools import fkik_switcher
from maya_psyhive.shows import vampirebloodline

from . import _fr_browser, _fr_tools
from ._fr_vendor_ma import FrasierVendorMa
from ._fr_work import FrasierWork, find_action_works, ASSETS, cur_work

ICON = icons.EMOJI.find('Brain')
_ROOT = ('P:/projects/frasier_38732V/code/primary/addons/general/'
         'frasier/_ToolsPsy')
_PY_ROOT = _ROOT+'/release/maya/v2018/hsl/python'
_INGEST_ROOT = 'P:/projects/frasier_38732V/production/vendor_in/Motion Burner'
_MOTIONBURNER_RIG = ('P:/projects/frasier_38732V/production/vendor_in/'
                     'Motion Burner/2020-02-11-BodyRig/SK_Tier1_Male_CR.ma')

_DUMMY = [FrasierWork, FrasierVendorMa, find_action_works,
          ASSETS, cur_work]  # For lint


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
        ma_.get_range(force=True)  # Update caches

    if apply_mapping:
        _apply_kealeye_rig_mapping()

    if legs_to_ik:
        _update_legs_to_ik()

    if save:
        _work = ma_.get_work()
        print ' - WORK', _work
        print ' - RANGE', ma_.get_range()
        host.save_scene(_work.path)
        _work.set_comment('Copied from '+ma_.path)
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
                raise RuntimeError('Error on loading scene '+path)

        assert host.get_fps() == 30

    # Update rig
    _ref = ref.find_ref()
    if not _ref.path == _MOTIONBURNER_RIG:
        _ref.swap_to(_MOTIONBURNER_RIG)


def _apply_kealeye_rig_mapping():
    """Apply rig mapping from Sean Kealeye MocapTools.

    This brings in the HSL rig, binds it to the MotionBurner skeleton,
    then bakes the anim. The MotionBurner rig is left in the scene
    for comparison but it is placed in a group and hidden.
    """
    _fr_tools.install_mocap_tools()
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


@py_gui.install_gui(
    browser={'fbx': py_gui.BrowserLauncher(
        default_dir='P:/projects/frasier_38732V')},
    label='Export HSL fbx')
def export_hsl_fbx(fbx=''):
    """Export an HSL format fbx.

    Args:
        fbx (str): path to export to
    """
    _fr_tools.export_hsl_fbx_from_cur_scene(fbx)


py_gui.set_section('Search')


@py_gui.install_gui(choices={
    'type_': ['Any', 'Vignette', 'Encounter', 'Disposition', 'Transition'],
    'format_': ['FBX (dated)', 'FBX', 'Full']})
def search_ingested_files(
        type_='Any', day='', fbx_filter='', ma_filter='',
        format_='FBX (dated)', refresh=True):
    """Search ingested files and print matches in given format.

    Args:
        type_ (str): only match fbxs of the given type
        day (str): match by delivery day (in %y%m%d format, eg. 200226)
        fbx_filter (str): filter by fbx path
        ma_filter (str): filter by vendor ma file path
        format_ (str): what data to print out
        refresh (bool): reread actions from disk
    """
    _works = []
    for _work in find_action_works(
            type_=None if type_ == 'Any' else type_, day_filter=day,
            fbx_filter=fbx_filter, ma_filter=ma_filter, version=1,
            force=refresh):
        try:
            _work.get_vendor_file()
        except CacheMissing:
            print '- MISSING VENDOR FILE', _work.path
            continue
        _works.append(_work)

    print

    for _idx, _work in enumerate(_works):

        if format_ == 'FBX (dated)':
            print '[{:d}/{:d}] {}'.format(
                _idx+1, len(_works), _work.get_export_fbx(dated=True).path)

        elif format_ == 'FBX':
            print '[{:d}/{:d}] {}'.format(
                _idx+1, len(_works), _work.get_export_fbx().path)

        elif format_ == 'Full':
            print '[{:d}/{:d}] {}'.format(
                _idx+1, len(_works), _work.get_export_fbx().basename)
            print ' - MA', _work.get_vendor_file()
            print ' - WORK', _work.path
            print ' - FBX', _work.get_export_fbx().path
            print

        else:
            raise ValueError(format_)


py_gui.set_section("Animation")


@py_gui.install_gui(label='Launch FK/IK switcher')
def launch_fkik_switcher():
    """Launch FK/IK switcher interface for HSL rig."""
    return fkik_switcher.launch_interface(
        system_=vampirebloodline.VampireFkIkSystem)


@py_gui.install_gui(label='Launch Action Browser')
def launch_action_browser():
    """Launch Action Browser interface."""
    _fr_browser.launch()


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
