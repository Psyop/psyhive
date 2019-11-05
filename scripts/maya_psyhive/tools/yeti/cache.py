"""Tools for managing yeti caching."""

import os
import shutil
import tempfile
import time

from maya import cmds

from psyhive import tk, host, qt, icons
from psyhive.utils import (
    abs_path, get_single, PyFile, Seq, safe_zip, test_path, lprint,
    seq_from_frame)

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import (
    get_parent, set_namespace, restore_sel, load_plugin, restore_frame)

ICON = icons.EMOJI.find('Ghost')


def _apply_cache(cache, yeti=None, ref_=None):
    """Apply a yeti cache.

    Args:
        cache (Seq): cache to apply
        yeti (HFnDependencyNode): for node to apply to
        ref_ (FileRef): reference to apply cache to
    """
    print 'APPLYING CACHE', cache

    # Get yeti node, creating if needed
    if yeti:
        _yeti = yeti
    else:
        _cache_ns = cache.output_name
        _ref = ref_ or ref.find_ref(_cache_ns)
        print ' - REF', _ref
        assert cache.channel.startswith(_cache_ns+'_')
        _node_name = cache.channel[len(_cache_ns+'_'):]
        _yeti = _ref.get_node(_node_name, catch=True)
        if not _yeti:
            _top_node = _ref.find_top_node()
            set_namespace(':'+_ref.namespace)
            _yeti = hom.CMDS.createNode('pgYetiMaya', name=_node_name)
            set_namespace(':')
            cmds.parent(get_parent(_yeti), _top_node)
    print ' - YETI', _yeti

    # Apply cache
    _yeti.plug('cacheFileName').set_val(cache.path)
    _yeti.plug('fileMode').set_val(1)
    _yeti.plug('overrideCacheWithInputs').set_val(False)


def _apply_caches_to_selected_asset(caches):
    """Apply yeti caches to the selected asset.

    The asset can be selected by selecting any node in the reference.

    If the asset doesn't have a matching yeti node, it will be created.

    Args:
        caches (TTOutputFileSeqBase list): caches to apply
    """

    # Get asset
    _ref = ref.get_selected(catch=True)
    if not _ref:
        qt.notify_warning(
            "No asset selected.\n\nPlease select the asset you apply the "
            "cache to.")
        return
    print 'REF', _ref

    # Apply caches to yeti nodes
    for _cache in caches:
        _apply_cache(_cache, ref_=_ref)


def _apply_caches_in_root_namespace(caches):
    """Apply yeti caches in the root namespace.

    Yeti nodes which don't currently exist will be created with no namespace.

    Args:
        caches (TTOutputFileSeqBase list): caches to apply
    """
    for _cache in caches:

        # Get node name
        _cache_ns = _cache.output_name
        assert _cache.channel.startswith(_cache_ns+'_')
        _node_name = _cache.channel[len(_cache_ns+'_'):]
        print 'NODE NAME', _node_name

        # Get yeti node
        load_plugin('pgYetiMaya')
        if cmds.objExists(_node_name):
            _yeti = hom.HFnDependencyNode(_node_name)
        else:
            _yeti = hom.CMDS.createNode('pgYetiMaya', name=_node_name)
        print 'YETI', _yeti

        _apply_cache(_cache, yeti=_yeti)


def _apply_viewport_updates():
    """Create a script job that runs on timeline update.

    This will update all cache paths on yeti nodes to match the current frame
    every time the timeline is updated. The purpose of this is to allow yeti
    nodes that have been created on the fly to update in the viewport.
    """
    _disable_viewport_updates()

    # Create new script job
    _cmd = time.strftime('\n'.join([
        '# PSYHIVE_YETI',
        'import {} as yeti'.format(__name__),
        'yeti.update_yeti_caches_to_cur_frame()',
    ]))
    _id = cmds.scriptJob(event=('timeChanged', _cmd), killWithScene=True)
    print 'CREATED SCRIPT JOB', _id


@restore_frame
@restore_sel
def _cache_yetis(yetis, apply_on_complete=False):
    """Cache a list of yeti nodes.

    Args:
        yetis (HFnDependencyNode list): nodes to cache
        apply_on_complete (bool): apply cache on completion
    """
    print 'CACHE YETIS', yetis
    _work = tk.cur_work()
    _yetis, _outs, _namespaces, _kwargs = _prepare_yetis_and_outputs(
        yetis=yetis, work=_work)

    # Get cache path - if multiple namespace need to cache to tmp
    _tmp_fmt = abs_path('{}/yetiTmp/<NAME>.%04d.cache'.format(
        tempfile.gettempdir()))
    if len(_namespaces) > 1:
        _cache_path = _tmp_fmt
        _tmp_dir = os.path.dirname(_tmp_fmt)
        shutil.rmtree(_tmp_dir)
        test_path(_tmp_dir)
    else:
        _cache_path = _work.map_to(
            _work.output_file_seq_type, output_name=get_single(_namespaces),
            channel='<NAME>', **_kwargs).path
    print "CACHE PATH", _cache_path

    # Generate caches
    for _yeti in _yetis:
        _yeti.plug('cacheFileName').set_val('')
        _yeti.plug('fileMode').set_val(0)
        _yeti.plug('overrideCacheWithInputs').set_val(False)
    cmds.select(_yetis)
    cmds.pgYetiCommand(
        writeCache=_cache_path, range=host.t_range(), samples=3)

    # Move tmp caches to outputs
    if len(_namespaces) > 1:
        for _out in _outs:
            _tmp_seq = Seq(_tmp_fmt.replace('<NAME>', _out.channel))
            for _frame, _tmp_path in safe_zip(
                    _tmp_seq.get_frames(), _tmp_seq.get_paths()):
                print _frame, _tmp_path
                shutil.move(_tmp_path, _out[_frame])

    # Apply cache to yeti nodes
    if apply_on_complete:
        for _yeti, _cache in safe_zip(_yetis, _outs):
            _apply_cache(cache=_cache, yeti=_yeti)


def _prepare_yetis_and_outputs(yetis, work):
    """Make sure all yetis are yeti shapes nodes and warn on output overwrite.

    Args:
        yetis (HFnDependencyNode list): nodes to cache
        work (TTWorkFileBase): work file being cached from

    Returns:
        (tuple): yeti nodes, outputs, namespaces, kwargs
    """
    _outs = []
    _namespaces = set()
    _force = False
    _yetis = []
    _kwargs = dict(format='fur', output_type='yeti', extension='fur')

    # Test outputs + tmp dirs
    for _yeti in yetis:

        if _yeti.object_type() == 'transform':
            _yeti = _yeti.shp
        _yetis.append(_yeti)

        # Map yeti node to output
        _namespaces.add(_yeti.namespace)
        _ref = ref.find_ref(_yeti.namespace)
        _out = work.map_to(
            work.output_file_seq_type, output_name=_ref.namespace,
            channel=str(_yeti).replace(':', '_'), **_kwargs)
        _out.test_dir()
        _outs.append(_out)
        print ' - OUT', _out

        # Warn on replace existing
        if _out.exists():

            # Get dialog result
            _buttons = ['Yes', 'Cancel']
            if len(yetis) > 1:
                _buttons.insert(1, 'Yes to all')
            _start, _end = _out.find_range()
            _result = 'Yes' if _force else qt.raise_dialog(
                'Replace existing {} cache ({:d}-{:d})?\n\n{}'.format(
                    _yeti, _start, _end, _out.path),
                title='Replace existing', buttons=_buttons,
                icon=icons.EMOJI.find("Ghost"))

            # Apply result
            if _result == 'Yes to all':
                _force = True
            elif _result == 'Yes':
                pass
            else:
                raise qt.DialogCancelled

            _out.delete(force=True)

    return _yetis, _outs, _namespaces, _kwargs


def _disable_viewport_updates():
    """Remove any existing yeti viewport update script job."""

    # Kill existing script job
    _existing_job = get_single([
        _job for _job in cmds.scriptJob(listJobs=True)
        if 'PSYHIVE_YETI' in _job], catch=True)
    if _existing_job:
        _id = int(_existing_job.split(':')[0])
        print 'KILLING JOB', _id
        cmds.scriptJob(kill=_id)
    else:
        print 'NO EXISTING JOB FOUND'

    # Revert any yeti nodes to %04d style cache
    for _yeti in hom.CMDS.ls(type='pgYetiMaya'):
        _cache = _yeti.plug('cacheFileName').get_val()
        _seq = seq_from_frame(_cache, catch=True)
        if _seq:
            _yeti.plug('cacheFileName').set_val(_seq.path)


def _find_yeti_caches(root):
    """Find yeti caches in the given root.

    This finds all output names which are yeti caches in all steps in
    the given asset/shot root.

    Args:
        root (TTRootBase): root to search

    Returns:
        (TTOutputNameBase list): caches
    """
    tk.clear_caches()
    _steps = root.find_step_roots()
    _names = []
    for _step in _steps:
        _names += [tk.obtain_cacheable(_name)
                   for _name in _step.find_output_names()
                   if _name.output_type == 'yeti']
    _names = [_name for _name in _names if _name.find_vers()]
    return _names


def update_yeti_caches_to_cur_frame(verbose=0):
    """Update yeti caches to point to the current frame.

    This is used in the script job which is triggered by timeline update.

    Args:
        verbose (int): print process data
    """
    _frame = int(round(cmds.currentTime(query=True)))
    lprint('UPDATE YETI CACHES', _frame, verbose=verbose)
    for _yeti in hom.CMDS.ls(type='pgYetiMaya'):
        print _yeti
        _file = _yeti.plug('cacheFileName').get_val()
        try:
            _seq = Seq(_file)
        except ValueError:
            _seq = seq_from_frame(_file)
        lprint(' -', _seq, verbose=verbose)
        _file = _seq[_frame]
        lprint(' -', _file, verbose=verbose)
        _yeti.plug('cacheFileName').set_val(_file)


def _write_cache_from_selected_assets(apply_on_complete=False):
    """Cache selected asset.

    All yeti nodes in the asset are cached.

    The asset can be selected by selecting any node in the reference.

    Args:
        apply_on_complete (bool): apply cache on completion
    """
    _refs = ref.get_selected(multi=True)
    if not _refs:
        qt.notify_warning("No assets selected.\n\nPlease select the assets "
                          "you want to cache.")
        return
    print 'REFS', _refs

    # Get yeti nodes
    _yetis = sum([_ref.find_nodes(type_='pgYetiMaya') for _ref in _refs], [])

    if not _yetis:
        qt.notify_warning(
            "No yeti nodes in assets:\n\n    {}\n\nNone of these assets can "
            "be cached.".format('\n    '.join([
                _ref.namespace for _ref in _refs])))
        return

    _cache_yetis(_yetis, apply_on_complete=apply_on_complete)


def _write_cache_from_selected_yetis(apply_on_complete=False):
    """Write a yeti cache from selected yeti nodes.

    Args:
        apply_on_complete (bool): apply cache on completion
    """
    _yetis = hom.get_selected(type_='pgYetiMaya', multi=True)
    if not _yetis:
        qt.notify_warning("No yeti nodes selected.\n\nPlease select one or "
                          "more yeti nodes.")
        return
    _cache_yetis(_yetis, apply_on_complete=apply_on_complete)


def _write_cache_from_all_yetis(apply_on_complete=False):
    """Write a yeti cache from all yeti nodes in the scene.

    Args:
        apply_on_complete (bool): apply cache on completion
    """
    _yetis = hom.CMDS.ls(type='pgYetiMaya')
    if not _yetis:
        qt.notify_warning("No yeti nodes in the scene.\n\nUnable to cache.")
        return
    _cache_yetis(_yetis, apply_on_complete=apply_on_complete)


class _YetiCacheToolsUi(qt.HUiDialog):
    """Interface for managing yeti caching."""

    def __init__(self):
        """Constructor."""
        self.work = tk.cur_work()
        self._yeti_caches = []

        _ui_file = abs_path(
            '{}/yeti_cache_tools.ui'.format(os.path.dirname(__file__)))
        super(_YetiCacheToolsUi, self).__init__(ui_file=_ui_file)
        self.set_icon(ICON)

        self.ui.step.currentTextChanged.connect(
            self.ui.asset.redraw)
        self.ui.asset.currentTextChanged.connect(
            self.ui.version.redraw)
        self.ui.version.currentIndexChanged.connect(
            self.ui.cache_read_asset.redraw)
        self.ui.version.currentIndexChanged.connect(
            self.ui.cache_read_root.redraw)
        self.ui.version.currentIndexChanged.connect(
            self.ui.version_label.redraw)

    def _redraw__step(self, widget):

        self._yeti_caches = _find_yeti_caches(root=self.work.root)

        # Update widget
        _steps = sorted(set([
            tk.obtain_cacheable(_name.get_step_root())
            for _name in self._yeti_caches]))
        for _step in _steps:
            widget.add_item(_step.name, data=_step)
        if not _steps:
            widget.addItem('<None>')
        widget.setEnabled(bool(_steps))

    def _redraw__asset(self, widget):

        _step = self.ui.step.selected_data()
        print 'STEP', _step

        _caches = [_cache for _cache in self._yeti_caches
                   if _cache.get_step_root() == _step]

        # Update widget
        widget.clear()
        for _cache in _caches:
            widget.add_item(_cache.output_name, data=_cache)
        if not _caches:
            widget.addItem('<None>')
        widget.setEnabled(bool(_caches))

        self.ui.version.redraw()

    def _redraw__version(self, widget):

        _cache = self.ui.asset.selected_data()
        print 'CACHE', _cache
        _vers = _cache.find_vers() if _cache else []

        # Update widget
        widget.clear()
        for _ver in _vers:
            widget.add_item(_ver.name, data=_ver)
        if _vers:
            widget.setCurrentIndex(len(_vers)-1)
        else:
            widget.addItem('<None>')
        widget.setEnabled(bool(_vers))

        self.ui.cache_read_asset.redraw()
        self.ui.cache_read_root.redraw()
        self.ui.version_label.redraw()

    def _redraw__version_label(self, widget):
        _ver = self.ui.version.selected_data()
        print 'VER', _ver
        if not _ver:
            _text = 'No versions found'
        else:
            _outs = _ver.find_outputs(output_type='yeti', format_='fur')
            if _outs:
                _text = 'Found frames {:d}-{:d}'.format(
                    *_outs[0].find_range())
            else:
                _text = 'No cache data found'
        widget.setText(_text)

    def _redraw__cache_read_asset(self, widget):
        _ver = self.ui.version.selected_data()
        widget.setEnabled(bool(_ver))

    _redraw__cache_read_root = _redraw__cache_read_asset

    def _callback__cache_write_assets(self):
        _apply_on_complete = self.ui.apply_on_complete.isChecked()
        _write_cache_from_selected_assets(apply_on_complete=_apply_on_complete)

    def _callback__cache_write_assets_help(self):
        _def = PyFile(__file__).find_def(
            _write_cache_from_selected_assets.__name__)
        qt.help_(_def.docs)

    def _callback__cache_write_node(self):
        _apply_on_complete = self.ui.apply_on_complete.isChecked()
        _write_cache_from_selected_yetis(apply_on_complete=_apply_on_complete)

    def _callback__cache_write_node_help(self):
        _def = PyFile(__file__).find_def(
            _write_cache_from_selected_yetis.__name__)
        qt.help_(_def.docs)

    def _callback__cache_write_all_nodes(self):
        _apply_on_complete = self.ui.apply_on_complete.isChecked()
        _write_cache_from_all_yetis(apply_on_complete=_apply_on_complete)

    def _callback__cache_write_all_nodes_help(self):
        _def = PyFile(__file__).find_def(
            _write_cache_from_all_yetis.__name__)
        qt.help_(_def.docs)

    def _callback__apply_viewport_updates(self):
        _apply_viewport_updates()

    def _callback__apply_viewport_updates_help(self):
        _def = PyFile(__file__).find_def(
            _apply_viewport_updates.__name__)
        qt.help_(_def.docs)

    def _callback__disable_viewport_updates(self):
        _disable_viewport_updates()

    def _callback__disable_viewport_updates_help(self):
        _def = PyFile(__file__).find_def(
            _disable_viewport_updates.__name__)
        qt.help_(_def.docs)

    def _callback__cache_read_asset(self):
        _ver = self.ui.version.selected_data()
        _outs = _ver.find_outputs(output_type='yeti', format_='fur')
        _apply_caches_to_selected_asset(caches=_outs)

    def _callback__cache_read_asset_help(self):
        _def = PyFile(__file__).find_def(
            _apply_caches_to_selected_asset.__name__)
        qt.help_(_def.get_docs().desc_full)

    def _callback__cache_read_root(self):
        _ver = self.ui.version.selected_data()
        _outs = _ver.find_outputs(output_type='yeti', format_='fur')
        _apply_caches_in_root_namespace(caches=_outs)

    def _callback__cache_read_root_help(self):
        _def = PyFile(__file__).find_def(
            _apply_caches_in_root_namespace.__name__)
        qt.help_(_def.get_docs().desc_full)


def launch_cache_tools():
    """Launch yeti cache tools interface."""

    # Make sure we are in a shot
    _work = tk.cur_work()
    if not _work:
        qt.notify_warning(
            'No current work file found.\n\nPlease save your scene.')
        return None

    # Launch interface
    from maya_psyhive.tools import yeti
    yeti.DIALOG = _YetiCacheToolsUi()
    return yeti.DIALOG
