"""Tools for frasier_38732V project."""

import operator
import os
import sys

from psyhive import icons, py_gui, qt
from psyhive.utils import CacheMissing, find, store_result, File, get_single

from maya_psyhive import ref
from maya_psyhive.tools import fkik_switcher
from maya_psyhive.shows import vampirebloodline
from maya_psyhive.utils import restore_sel

from . import _fr_browser, _fr_tools, _fr_ingest
from ._fr_vendor_ma import FrasierVendorMa
from ._fr_work import (
    FrasierWork, find_action_works, ASSETS, cur_work, EXPORT_FBX_ROOT)
from ._fr_ingest import ingest_ma_files_to_pipeline, CAM_SETTINGS_FMT

ICON = icons.EMOJI.find('Brain')
BUTTON_LABEL = 'frasier\ntools'

_ROOT = ('P:/projects/frasier_38732V/code/primary/addons/general/'
         'frasier/_ToolsPsy')
_PY_ROOT = _ROOT+'/release/maya/v2018/hsl/python'
_INGEST_ROOT = 'P:/projects/frasier_38732V/production/vendor_in/Motion Burner'

__ALL__ = [FrasierWork, FrasierVendorMa, find_action_works,
           ASSETS, cur_work, EXPORT_FBX_ROOT, CAM_SETTINGS_FMT]  # For lint


py_gui.set_section("Ingestion tools")


@py_gui.install_gui(
    browser={'ma_': py_gui.BrowserLauncher(default_dir=_INGEST_ROOT)},
    label='Prepare MotionBurner ma file')
def prepare_motionburner_ma_file(
        ma_, fix_hik_issues=True, use_hsl_rig=True, legs_to_ik=False):
    """Prepare MotionBurner ma file from vendor in.

    This opens the scene and updates the broken rig reference to the one on
    our file system.

    Args:
        ma_ (str): path to ma file to load
        fix_hik_issues (bool): check and fix any human ik issues
        use_hsl_rig (bool): update the rig to HSL rig
        legs_to_ik (bool): update legs from fk to ik for animation (slow)
    """
    _ma = None
    if ma_:
        _fr_ingest.load_vendor_ma(ma_, fix_hik_issues=fix_hik_issues)
        _ma = FrasierVendorMa(ma_)
    _fr_ingest.ingest_ma(ma_=_ma, legs_to_ik=legs_to_ik, save=False,
                         apply_mapping=use_hsl_rig, load_ma=False)


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


py_gui.set_section('Batch ingestion')


@py_gui.install_gui(
    choices={"verbose": range(2)},
    browser={'src_dir': py_gui.BrowserLauncher(
        default_dir=_INGEST_ROOT, mode='SingleDirExisting')})
def ingest_ma_files_to_pipeline_(
        src_dir, ma_filter='', replace=False, blast_=True, legs_to_ik=False,
        verbose=0):
    """Copy ma file from vendors_in to psyop pipeline.

    This creates a work file for each ma file and  also generates face/body
    blasts.

    Args:
        src_dir (str): vendor in directory to search for ma files
        ma_filter (str): apply filter to ma file path
        replace (bool): overwrite existing files
        blast_ (bool): execute blasts
        legs_to_ik (bool): execute legs ik switch (slow)
        verbose (int): print process data
    """
    ingest_ma_files_to_pipeline(**locals())


py_gui.set_section('Search')


@py_gui.install_gui(choices={
    'type_': ['Any', 'Vignette', 'Encounter', 'Disposition', 'Transition'],
    'format_': ['Vendor MA', 'FBX (dated)', 'FBX', 'Full']})
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

    if format_ == 'Vendor MA':
        _works.sort(key=operator.methodcaller('get_vendor_file'))
    elif format_ == 'FBX (dated)':
        _sort = lambda work: work.get_export_fbx(dated=True)
        _works.sort(key=_sort)

    for _idx, _work in enumerate(_works):

        _prefix = '[{:d}/{:d}]'.format(_idx+1, len(_works))

        if format_ == 'FBX (dated)':
            print _prefix, _work.get_export_fbx(dated=True).path

        elif format_ == 'FBX':
            print _prefix, _work.get_export_fbx().path

        elif format_ == 'Vendor MA':
            print _prefix, _work.get_vendor_file()

        elif format_ == 'Full':
            print _prefix, _work.get_export_fbx().basename
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


@store_result
def _find_rigs():
    """Find HSL rigs to switch between.

    Returns:
        (File list): list of rig files
    """
    _path = 'P:/projects/frasier_38732V/production/character_rigs'
    _files = find(_path, depth=1, type_='f', extn='ma', class_=File)
    for _file in _files:
        _file.name = _file.basename.replace('SK_', '').replace('_', ' ')
    return _files


@restore_sel
@py_gui.install_gui(choices={'rig': [_rig.name for _rig in _find_rigs()]})
def switch_selected_rig(rig):
    """Switch selected rig reference.

    Args:
        rig (str): rig name to switch to
    """
    _sel = ref.get_selected(catch=True)
    if not _sel:
        qt.notify_warning('No rig selected')
        return
    print 'SELECTED', _sel
    _trg = get_single([_rig for _rig in _find_rigs() if _rig.name == rig])
    print 'TARGET', _trg.path
    qt.ok_cancel('Update "{}" rig to "{}"?'.format(_sel.namespace, _trg.name))
    _sel.swap_to(_trg.path)


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
