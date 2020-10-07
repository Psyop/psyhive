"""Tools for managing the yeti cache iterface."""

import os

from psyhive import tk2, qt, icons
from psyhive.utils import abs_path, PyFile, get_single

from .yeti_viewport import (
    apply_viewport_updates, disable_viewport_updates)
from .yeti_read import (
    find_yeti_caches, apply_caches_to_sel_asset,
    apply_caches_in_root_namespace)
from .yeti_write import (
    write_cache_from_sel_assets, write_cache_from_sel_yetis,
    write_cache_from_all_yetis)

from . import yeti_write, yeti_read, yeti_viewport

ICON = icons.EMOJI.find('Ghost')
DIALOG = None


class _YetiCacheToolsUi(qt.HUiDialog3):
    """Interface for managing yeti caching."""

    def __init__(self):
        """Constructor."""
        self.work = tk2.cur_work()
        self._yeti_caches = []

        _ui_file = abs_path(
            '{}/yeti_cache_tools.ui'.format(os.path.dirname(__file__)))
        super(_YetiCacheToolsUi, self).__init__(ui_file=_ui_file)
        self.set_icon(ICON)

        self._redraw__Step()

        self.ui.Step.currentTextChanged.connect(
            self._redraw__Name)
        self.ui.Name.currentTextChanged.connect(
            self._redraw__Version)
        self.ui.Version.currentIndexChanged.connect(
            self._redraw__CacheReadAsset)
        self.ui.Version.currentIndexChanged.connect(
            self._redraw__CacheReadRoot)
        self.ui.Version.currentIndexChanged.connect(
            self._redraw__VersionLabel)

    def _redraw__Step(self):

        self._yeti_caches = find_yeti_caches(root=self.work.get_root())

        # Update widget
        _steps = sorted(set([_ver.step for _ver in self._yeti_caches]))
        for _step in _steps:
            self.ui.Step.add_item(_step)
        if not _steps:
            self.ui.Step.addItem('<None>')
        self.ui.Step.setEnabled(bool(_steps))

        self._redraw__Name()

    def _redraw__Name(self):

        _step = self.ui.Step.currentText()

        _names = sorted(set([
            tk2.TTOutputName(_ver.dir) for _ver in self._yeti_caches
            if _ver.step == _step]))

        # Update widget
        _select = None
        self.ui.Name.clear()
        for _name in _names:
            self.ui.Name.add_item(_name.basename, data=_name)
            if not _select and _name.task == tk2.cur_work().task:
                _select = _name
        if _select:
            self.ui.Name.select_data(_select)
        if not _names:
            self.ui.Name.addItem('<None>')
        self.ui.Name.setEnabled(bool(_names))

        self._redraw__Version()

    def _redraw__Version(self):

        _step = self.ui.Step.currentText()
        _name = self.ui.Name.selected_data()
        _vers = [_ver for _ver in self._yeti_caches
                 if _ver.step == _step and
                 tk2.TTOutputName(_ver) == _name]

        # Update widget
        self.ui.Version.clear()
        for _ver in _vers:
            self.ui.Version.add_item(_ver.filename, data=_ver)
        if _vers:
            self.ui.Version.setCurrentIndex(len(_vers)-1)
        else:
            self.ui.Version.addItem('<None>')
        self.ui.Version.setEnabled(bool(_vers))

        self._redraw__CacheReadAsset()
        self._redraw__CacheReadRoot()
        self._redraw__VersionLabel()

    def _redraw__VersionLabel(self):
        _ver = self.ui.Version.selected_data()
        # print 'VER', _ver
        if not _ver:
            _text = 'No versions found'
        else:
            _out = get_single(_ver.find_files(), catch=True)
            if _out:
                _text = 'Found frames {:d}-{:d}'.format(
                    *_out.find_range())
            else:
                _text = 'No cache data found'
        self.ui.VersionLabel.setText(_text)

    def _redraw__CacheReadAsset(self):
        _ver = self.ui.Version.selected_data()
        self.ui.CacheReadAsset.setEnabled(bool(_ver))

    _redraw__CacheReadRoot = _redraw__CacheReadAsset

    def _callback__ApplyViewportUpdates(self):
        apply_viewport_updates()

    def _callback__ApplyViewportUpdatesHelp(self):
        _def = PyFile(yeti_viewport.__file__).find_def(
            apply_viewport_updates.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)

    def _callback__CacheWriteAssets(self):
        _samples = self.ui.Samples.value()
        _apply_on_complete = self.ui.ApplyOnComplete.isChecked()
        _outs = write_cache_from_sel_assets(
            apply_on_complete=_apply_on_complete, samples=_samples)
        self._redraw__Step()

    def _callback__CacheWriteAssetsHelp(self):
        _def = PyFile(yeti_write.__file__).find_def(
            write_cache_from_sel_assets.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)

    def _callback__CacheWriteNode(self):
        _samples = self.ui.Samples.value()
        _apply_on_complete = self.ui.ApplyOnComplete.isChecked()
        write_cache_from_sel_yetis(
            apply_on_complete=_apply_on_complete, samples=_samples)
        self._redraw__Step()

    def _callback__CacheWriteNodeHelp(self):
        _def = PyFile(yeti_write.__file__).find_def(
            write_cache_from_sel_yetis.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)

    def _callback__CacheWriteAllNodes(self):
        _samples = self.ui.Samples.value()
        _apply_on_complete = self.ui.ApplyOnComplete.isChecked()
        write_cache_from_all_yetis(
            apply_on_complete=_apply_on_complete, samples=_samples)
        self._redraw__Step()

    def _callback__CacheWriteAllNodesHelp(self):
        _def = PyFile(yeti_write.__file__).find_def(
            write_cache_from_all_yetis.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)

    def _callback__CacheReadAsset(self):
        _ver = self.ui.Version.selected_data()
        _outs = _ver.find_files(format_='yeti')
        apply_caches_to_sel_asset(caches=_outs)

    def _callback__CacheReadAssetHelp(self):
        _def = PyFile(yeti_read.__file__).find_def(
            apply_caches_to_sel_asset.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)

    def _callback__CacheReadRoot(self):
        print 'APPLY CACHES IN ROOT'
        _ver = self.ui.Version.selected_data()
        print ' - VER', _ver
        _outs = _ver.find_files(format_='yeti')
        print ' - OUTS', _outs
        apply_caches_in_root_namespace(caches=_outs)

    def _callback__CacheReadRootHelp(self):
        _def = PyFile(yeti_read.__file__).find_def(
            apply_caches_in_root_namespace.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)

    def _callback__CacheUpdateAll(self):
        yeti_read.update_all(parent=self)

    def _callback__CacheUpdateAllHelp(self):
        _def = PyFile(yeti_read.__file__).find_def(
            yeti_read.update_all.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)

    def _callback__DisableViewportUpdates(self):
        disable_viewport_updates()

    def _callback__DisableViewportUpdatesHelp(self):
        _def = PyFile(yeti_viewport.__file__).find_def(
            disable_viewport_updates.__name__)
        qt.help_(_def.docs.split('Args:')[0].strip(), parent=self)


def launch_cache_tools():
    """Launch yeti cache tools interface."""
    global DIALOG

    # Make sure we are in a shot
    _work = tk2.cur_work()
    if not _work:
        qt.notify_warning(
            'No current work file found.\n\nPlease save your scene.')
        return None

    # Launch interface
    from maya_psyhive.tools import yeti
    DIALOG = _YetiCacheToolsUi()
    yeti.DIALOG = DIALOG
    return yeti.DIALOG
