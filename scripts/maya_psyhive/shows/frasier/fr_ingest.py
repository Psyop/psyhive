"""Ingestion tools for Frasier.

These are used to manage the flow of data from ma files in the date stamped
folders in the vendor_in directory, to psyop pipeline work files with output
file sequences as blasts, and the exported to fbx in the processed_fbx folder.
"""

import os
import tempfile

from maya import cmds, mel
from pymel import core as pm

import psylaunch

from psyhive import icons, qt, host
from psyhive.utils import find, abs_path, lprint, passes_filter, Seq

from maya_psyhive import ref, open_maya as hom, ui
from maya_psyhive.tools import fkik_switcher
from maya_psyhive.shows import vampirebloodline
from maya_psyhive.utils import blast, pause_viewports_on_exec

from . import fr_vendor_ma, fr_tools

ICON = icons.EMOJI.find('Brain')

MOBURN_RIG = ('P:/projects/frasier_38732V/production/vendor_in/'
              'Motion Burner/2020-02-11-BodyRig/SK_Tier1_Male_CR.ma')
MOBURN_RIG = (r"P:\projects\frasier_38732V\production\vendor_in"
              r"\Motion Burner\Faceware_2020-04-28\SK_Tier1_Male_CR3.ma")
MOBURN_RIG = ("P:/projects/frasier_38732V/production/kealeye_tools"
              "/MocapTools/Data/CaptureRig/SK_Tier1_Male_CR.ma")

_DIR = abs_path(os.path.dirname(__file__))
CAM_SETTINGS_FMT = abs_path(
    '_fr_{}_cam_{}.preset', root=os.path.dirname(__file__))


def ingest_ma(ma_, load_ma=True, force=False, apply_mapping=True,
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

        # Try to get around hanging issues
        print 'NEW SCENE'
        host.new_scene(force=force)
        print 'INGEST', ma_
        load_vendor_ma(ma_.path, force=True)
        ma_.get_range(force=True)  # Update caches

    if apply_mapping:
        _apply_kealeye_rig_mapping()

    if legs_to_ik:
        _update_legs_to_ik()

    _work = ma_.get_work()
    print ' - WORK', _work
    print ' - RANGE', ma_.get_range()

    if save:
        host.save_scene(_work.path)
        _work.set_comment('Copied from '+ma_.path)
        _work.set_vendor_file(ma_.path)
        assert _work.get_vendor_file() == ma_.path
        assert _work.get_export_fbx(dated=True)  # Check timestamp
        _work.has_ik_legs()  # Store cache
        if legs_to_ik:
            assert _work.has_ik_legs()

    return _work


def load_vendor_ma(path, fix_hik_issues=False, force=False, lazy=False):
    """Load vendor ma file.

    The file is loaded and then the bad rig reference is updated.

    Args:
        path (str): vendor ma file
        fix_hik_issues (bool): check if hik is still driving the motion
            burner skeleton and disable it if it is
        force (bool): lose unsaved changes with no warning
        lazy (bool): don't open scene if it's already open
    """

    # Load scene
    if not lazy or host.cur_scene() != path:

        if not force:
            host.handle_unsaved_changes()

        # Load the scene
        try:
            pause_viewports_on_exec(cmds.file)(
                path, open=True, prompt=False, force=True)
        except RuntimeError as _exc:
            if "has no '.ai_translator' attribute" in _exc.message:
                pass
            else:
                print '######################'
                print _exc.message
                print '######################'
                raise RuntimeError('Error on loading scene '+path)

        assert host.get_fps() == 30

    _fix_cr_namespaces()

    # Update rig
    _ref = ref.find_ref(filter_='-camera -cemera')
    if not _ref.path == MOBURN_RIG:
        _ref.swap_to(MOBURN_RIG)
    _ref = _fix_nested_namespace(_ref)
    if not _ref.namespace == 'SK_Tier1_Male_CR':
        _ref.rename('SK_Tier1_Male_CR')

    # Test for hik issues
    if fix_hik_issues:
        _test_for_hik_issues(_ref)


def _fix_cr_namespaces():
    """Fix namespaces with _CR tag in.

    This namespace should only appear after the Kealeye tools have brought
    in the HSL rig. Having a namespace with that tag in will confuse the
    retargetting.
    """
    for _ns in cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True):
        if '_CR' not in _ns:
            continue
        print 'FIXING _CR NAMESPACE', _ns
        cmds.namespace(moveNamespace=(_ns, ':'), force=True)
        assert not cmds.ls(_ns+":*")
        cmds.namespace(removeNamespace=_ns)


def _fix_nested_namespace(ref_):
    """Fix nested namespace issues.

    If the rig is in a nested namespace, move it into the root namespace.

    Args:
        ref_ (FileRef): reference to check

    Returns:
        (FileRef): fixed reference
    """
    _ref_node = hom.HFnDependencyNode(ref_.ref_node)
    if not _ref_node.namespace:
        print 'NO NAMESPACE ISSUE TO FIX'
        return ref_

    print 'FIXING NESTED NAMESPACE', _ref_node.namespace
    cmds.namespace(moveNamespace=(_ref_node.namespace, ":"), force=True)
    return ref.find_ref()


def _test_for_hik_issues(ref_):
    """Fix any human ik issues.

    Some MotionBurner files have been delivered with human ik left driving
    the MotionBurner skeleton. This will check for any human ik driver and
    disable it if it is found.

    Args:
        ref_ (FileRef): reference to update
    """
    _hip_rx = ref_.get_plug('Hip_L.rx')
    if _hip_rx.list_incoming(type='animCurve'):
        print 'NO HIK ISSUES'
        return

    print 'HIK ISSUES DETECTED'

    # Find source option menu
    mel.eval('HIKCharacterControlsTool')
    _hik_src_opt = None
    for _grp in cmds.lsUI(long=True, type='optionMenuGrp'):
        if _grp.endswith('|hikSourceList'):
            _hik_src_opt = _grp.split('|')[-1]
            break
    assert _hik_src_opt
    print 'HIK SOURCE OPTION', _hik_src_opt

    # Apply None
    cmds.optionMenuGrp(_hik_src_opt, edit=True, value=" None")
    mel.eval("hikUpdateCurrentSourceFromUI()")
    mel.eval("hikUpdateContextualUI()")

    # assert _hip_rx.list_incoming(type='animCurve')
    print 'DISABLED HUMAN IK'


@pause_viewports_on_exec
def _apply_kealeye_rig_mapping():
    """Apply rig mapping from Sean Kealeye MocapTools.

    This brings in the HSL rig, binds it to the MotionBurner skeleton,
    then bakes the anim. The MotionBurner rig is left in the scene
    for comparison but it is placed in a group and hidden.
    """
    print 'APPLY KEALEYE RIG MAP'
    assert cmds.ogs(query=True, pause=True)
    fr_tools.install_mocap_tools()
    from MocapTools.Scripts import PsyopMocapTools

    # Apply kealeye bake
    print 'BAKING CONTROL RIG SCENE'
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


def _find_ma_files_to_check(src_dir, ma_filter, work_filter, limit):
    """Get list of ma files to check.

    Args:
        src_dir (str): vendor in directory to search for ma files
        ma_filter (str): apply filter to ma file path
        work_filter (str): apply filter to work file path
        limit (int): limit the number of files to be processed

    Returns:
        (FrasierVendorMa list): list of files to check
    """
    assert os.path.exists(src_dir)
    _mas = find(src_dir, extn='ma', type_='f', filter_=ma_filter,
                class_=fr_vendor_ma.FrasierVendorMa)
    if work_filter:
        _mas = [_ma for _ma in _mas
                if passes_filter(_ma.get_work().path, work_filter)]
    if limit:
        _mas = _mas[:limit]

    return _mas


def ingest_ma_files_to_pipeline(
        src_dir=('P:/projects/frasier_38732V/production/vendor_in/'
                 'Motion Burner/Delivery_2020-02-12'),
        ma_filter='', work_filter='', replace=False, blast_=False,
        legs_to_ik=False, reverse=False, limit=0, verbose=0):
    """Copy ma file from vendors_in to psyop pipeline.

    This creates a work file for each ma file and  also generates face/body
    blasts.

    Args:
        src_dir (str): vendor in directory to search for ma files
        ma_filter (str): apply filter to ma file path
        work_filter (str): apply filter to work file path
        replace (bool): overwrite existing files
        blast_ (bool): execute blasts
        legs_to_ik (bool): execute legs ik switch (slow)
        reverse (bool): reverse the list (for parallel processing)
        limit (int): limit the number of files to be processed
        verbose (int): print process data
    """
    _src_dir = abs_path(src_dir)
    print 'SRC DIR', _src_dir
    assert os.path.exists(_src_dir)
    _mas = _find_ma_files_to_check(_src_dir, ma_filter, work_filter, limit)

    # Check which mas need processing
    _to_process = []
    _overwrites = []
    _replacing = []
    for _idx, _ma in qt.progress_bar(
            enumerate(_mas), 'Checking {:d} ma files'):
        lprint(
            'PROCESSING MA {:d}/{:d} {}\n - MA {}'.format(
                _idx+1, len(_mas), _ma.filename, _ma.path),
            verbose=verbose)

        # Check for overwrite
        _work = _ma.get_work()
        lprint(' - WORK', _work.path, verbose=verbose)
        if _work.exists():
            _vendor_file = _work.get_vendor_file()
            if replace or _ma.path != _work.get_vendor_file():
                _overwrites.append((_ma, _work))
                if len(_work.find_vers()) > 1:
                    _replacing.append((_ma, _work))
            elif (
                    _work.blast_comp.exists() and
                    _work.get_export_fbx().exists() and
                    _work.get_export_fbx(dated=True).exists()):
                print ' - COMP BLAST', _work.blast_comp.path
                print ' - FBX', _work.get_export_fbx().path
                print ' - NO PROCESSING NEEDED'
                continue

        _to_process.append([_ma, _work])

        print

    print
    print
    print 'FOUND {:d} FILES TO PROCESS'.format(len(_to_process))
    print

    # Remove any data to be replaced
    if _replacing:
        _text = 'Replacing {:d} files:\n\n'.format(len(_replacing))
        for _ma, _work in _replacing:
            _text += '\n - MA {}\n - WORK {}\n\n'.format(_ma.path, _work.path)
        qt.ok_cancel(_text)
    if _overwrites:
        _remove_existing_data(_overwrites)

    # Execute the ingestion
    if not _to_process:
        return
    qt.ok_cancel('Ingest {:d} files?'.format(len(_to_process)), icon=ICON)
    if reverse:
        _to_process = reversed(_to_process)
    for _ma, _work in qt.progress_bar(
            _to_process, 'Ingesting {:d} ma{}', col='LightSkyBlue'):
        _ingest_vendor_ma(ma_=_ma, work=_work, blast_=blast_,
                          legs_to_ik=legs_to_ik)


def _remove_existing_data(overwrites):
    """Remove existing ingestion data on items to be replaced.

    Args:
        overwrites (tuple list): list of ma/work files
    """
    print 'OVERWRITES:'
    for _ma, _work in overwrites:
        print _work.path
        print ' - CUR', _work.get_vendor_file()
        print ' - NEW', _ma.path
        print

    qt.ok_cancel("Overwrite {:d} work files?".format(len(overwrites)))
    for _, _work in qt.progress_bar(overwrites, "Cleaning {:d} work{}"):
        _work.delete_all_data(force=True)
    print


def _ingest_vendor_ma(ma_, work, blast_, legs_to_ik):
    """Ingest a vendor ma file.

    Args:
        ma_ (FrasierVendorMa): source ma file
        work (FrasierWork): work file to ingest to
        blast_ (bool): execute blasting
        legs_to_ik (bool): execute legs ik switch (slow)
    """
    print 'VENDOR FILE', ma_.path

    # Ingest work
    _work = work
    if not work.exists():
        _work = ingest_ma(ma_=ma_, force=True, legs_to_ik=legs_to_ik)
    print ' - WORK', work.path
    print ' - RANGE', work.get_range()

    if blast_:

        # Generate blast
        if not work.blast.exists():
            _blast_work(work, force=True)
        else:
            print ' - BLAST', work.blast.find_range(), work.blast.path

        # Generate face blast
        if not work.face_blast.exists():
            _face_blast_work(work, force=True)
        else:
            print ' - FACE BLAST {} {}'.format(
                work.face_blast.find_range(), work.face_blast.path)

        # Generate blast comp
        if not work.blast_comp.exists():
            _generate_blast_comp_mov(work)
        else:
            print ' - FACE BLAST {}'.format(work.blast_comp.path)

    # Generate export fbx
    if not (_work.get_export_fbx().exists() and
            _work.get_export_fbx(dated=True).exists()):
        _generate_fbx(_work, force=True)
    else:
        print ' - FBX {}'.format(work.get_export_fbx().path)

    print


def _blast_work(work, seq=None, build_cam_func=None, view=False, force=False,
                blast_=True, verbose=0):
    """Blast the given work file.

    Args:
        work (FrasierWork): work file to blast
        seq (TTOutputFileSeq): output image sequence
        build_cam_func (fn): function to build blast cam
        view (bool): view images on blast
        force (bool): force overwrite existing images
        blast_ (bool): execute blast
        verbose (int): print process data
    """
    _seq = seq or work.blast

    if cmds.ogs(query=True, pause=True):
        cmds.ogs(pause=True)
    assert not cmds.ogs(query=True, pause=True)

    print 'BLAST', _seq
    print ' - FRAMES', _seq.find_range()
    if not force and _seq.exists(verbose=1):
        print ' - ALREADY EXISTS'
        return

    if not host.cur_scene() == work.path:
        cmds.file(work.path, open=True, prompt=False, force=force)

    _build_cam_func = build_cam_func or _build_blast_cam
    _cam = _build_cam_func()
    print ' - CAM', _cam, type(_cam)

    # Look through cam
    _panel = ui.get_active_model_panel()
    _editor = ui.get_active_model_panel(as_editor=True)
    cmds.modelPanel(_panel, edit=True, camera=_cam)
    cmds.refresh()
    _cur_cam = cmds.modelPanel(_panel, query=True, camera=True)
    print ' - CUR CAM', _cur_cam
    assert _cur_cam == _cam

    # Apply blast settings
    cmds.modelEditor(_editor, edit=True, grid=False, locators=False,
                     cameras=False, nurbsCurves=False, dimensions=False,
                     joints=False)
    cmds.camera(_cam, edit=True, displayFilmGate=False,
                displayResolution=False, overscan=1)
    pm.PyNode("hardwareRenderingGlobals").multiSampleEnable.set(True)
    cmds.setAttr(_cam.shp+'.nearClipPlane', 0.5)

    # Execute blast
    if not blast_:
        return
    blast(seq=_seq, res=(1280, 720), verbose=verbose)
    if view:
        _seq.view()
    print ' - BLASTED', _seq


def _face_blast_work(work, blast_=True, view=False, force=False):
    """Generate face blast for the given work file.

    Args:
        work (FrasierWork): work file to blast
        blast_ (bool): execute blast
        view (bool): view images on blast
        force (bool): force replace existing blast
    """
    print 'FACE BLAST', work.face_blast
    _blast_work(work=work, view=view, seq=work.face_blast, blast_=blast_,
                build_cam_func=_build_face_blast_cam, force=force)


def _build_face_blast_cam():
    """Build face blast camera.

    Returns:
        (HFnCamera): face blast cam
    """
    _cam = hom.CMDS.camera(name='FACE_CAM')
    _panel = ui.get_active_model_panel()
    cmds.modelPanel(_panel, edit=True, camera=_cam)
    cmds.parent(_cam, 'SK_Tier1_Male:Head_M', relative=False)
    cmds.setAttr(_cam+'.translate', -2.9, 54.3, 0.0)
    cmds.setAttr(_cam+'.rotate', -56, -90, -25)

    _cam = _cam.rename('FACE_CAM')

    return _cam


def _build_blast_cam():
    """Build blast camera.

    Returns:
        (HFnCamera): blast cam
    """
    _cam = hom.CMDS.camera(name='BLAST_CAM')
    for _node, _name in [(_cam.tfm, 'tfm'), (_cam.shp, 'shp')]:
        _preset = CAM_SETTINGS_FMT.format('blast', _name)
        print _preset
        hom.HFnDependencyNode(str(_node)).load_preset(_preset)

    _cam = _cam.rename('BLAST_CAM')

    return _cam


def _get_ref_jpgs(mov, start, secs):
    """Get reference mov jpg sequence.

    If no reference mov was found, None is returns. Otherwise, the
    section of the reference mov relating to this work (based on
    ref_movs.data spreadsheet) is baked out to a tmp jpg sequence.

    Args:
        mov (str): path to mov to extract
        start (float): start seconds
        secs (float): duration of section to bake

    Returns:
        (Seq|None): tmp reference jpgs (if any)
    """
    print ' - MOV', start, mov

    # Prepare tmp seq
    _ref_tmp_jpgs = Seq(abs_path('{}/ref_tmp/images.%04d.jpg'.format(
        tempfile.gettempdir())))
    _ref_tmp_jpgs.test_dir()
    _ref_tmp_jpgs.delete(force=True)

    # Run ffmpeg
    _args = [
        '-i', mov,
        '-vf', "fps=30,select='between(t,{:.02f},{:.02f})'".format(
            start, start+secs),
        '-vsync', '0', _ref_tmp_jpgs.path,
    ]
    print 'launch ffmpeg --', ' '.join(_args)
    psylaunch.launch_app('ffmpeg', args=_args, wait=True)
    print ' - WROTE TO', _ref_tmp_jpgs.path
    print ' - REF JPGS {} {}'.format(
        _ref_tmp_jpgs.find_range(force=True), _ref_tmp_jpgs.path)

    return _ref_tmp_jpgs


def _generate_blast_comp_mov(
        work, ref_imgs=True, comp_imgs=True, margin=20, thumb_aspect=0.75):
    """Generate blast comp mov file for the given work.

    Args:
        work (FrasierWork): work file to comp images for
        ref_imgs (bool): generate ref jpgs (disable for debugging)
        comp_imgs (bool): generate comp jpgs (disable for debugging)
        margin (int): face ref/blast overlay margin in pixels
        thumb_aspect (float): aspect ration of face ref/blast overlay
    """
    print 'WORK', work.path

    assert work.blast.exists()
    assert work.face_blast.exists()
    assert not work.blast_comp.exists()

    _start, _end = work.blast.find_range()
    _dur_secs = 1.0*(_end - _start + 1)/30

    print ' - BLAST COMP', work.blast_comp.path
    print ' - RANGE {:d}-{:d} ({:.02f}s)'.format(_start, _end, _dur_secs)

    # Generate tmp ref jpgs
    if ref_imgs and work.get_ref_mov():
        _mov, _start = work.get_ref_data()
        _ref_tmp_jpgs = _get_ref_jpgs(mov=_mov, start=_start, secs=_dur_secs)
    else:
        _ref_tmp_jpgs = Seq(abs_path('{}/ref_tmp/images.%04d.jpg'.format(
            tempfile.gettempdir())))
        _ref_tmp_jpgs.delete(force=True)
    print ' - REF JPG', _ref_tmp_jpgs

    # Build comp jpgs
    _comp_tmp_jpgs = Seq(abs_path('{}/comp_tmp/images.%04d.jpg'.format(
        tempfile.gettempdir())))
    if comp_imgs:

        _comp_tmp_jpgs.test_dir()
        _comp_tmp_jpgs.delete(force=True)

        for _idx, _src_frame in qt.progress_bar(
                enumerate(work.blast.get_frames()),
                'Comping {:d} images', stack_key='FrasierBlastComp',
                col='GreenYellow'):

            _out = qt.HPixmap(work.blast[_src_frame])
            _face = qt.HPixmap(work.face_blast[_src_frame])
            _thumb_w = (1.0*_out.width()/3 - margin*3)/2
            _thumb_size = qt.get_size(_thumb_w, _thumb_w/thumb_aspect)

            # Add ref overlay
            if _ref_tmp_jpgs:
                _ref = qt.HPixmap(_ref_tmp_jpgs[_idx+1])
                _ref = _ref.resize(_thumb_size)
                _out.add_overlay(_ref, pos=(_out.width()*2/3 + margin, margin))

            # Add face blast overlay
            _face_size = qt.get_size(
                _face.height()*thumb_aspect, _face.height())
            _face = _face.copy(
                _face.width()/2 - _face_size.width()/2, 0,
                _face_size.width(), _face_size.height())
            _face = _face.resize(_thumb_size)
            _out.add_overlay(
                _face, pos=(_out.width()-margin, margin), anchor="TR")

            _out.save(_comp_tmp_jpgs[_idx+1])
        print ' - WROTE TMP IMAGES', _comp_tmp_jpgs.path
    print ' - COMP IMAGES {} {}'.format(
        _comp_tmp_jpgs.find_range(force=True), _comp_tmp_jpgs.path)

    # Compile out mov
    work.blast_comp.test_dir()
    _args = [
        '-r', '30',
        '-f', 'image2',
        '-i', _comp_tmp_jpgs.path,
        '-vcodec', 'libx264',
        '-crf', '25',
        '-pix_fmt', 'yuv420p',
        work.blast_comp.path]
    print 'launch ffmpeg --', ' '.join(_args)
    psylaunch.launch_app('ffmpeg', args=_args, wait=True)
    assert work.blast_comp.exists()
    print ' - WROTE MOV', work.blast_comp.path


def _generate_fbx(work, load_scene=True, lazy=True, force=False):
    """Generate fbx for a work file.

    Args:
        work (FrasierWork): work file to generate for
        load_scene (bool): load scene before export (for debugging)
        lazy (bool): don't load file if it's already open
        force (bool): overwrite existing files without confirmation
    """
    print 'EXPORT FBX'

    if load_scene:
        if not lazy or host.cur_scene() != work.path:
            print ' - LOADING SCENE FOR FBX EXPORT'
            host.open_scene(work.path, force=True)

    work.export_fbx(force=force)
