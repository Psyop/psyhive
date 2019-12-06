"""Tools for managing the yeti cache iterface."""

import os

from psyhive import tk, qt, icons
from psyhive.utils import abs_path, PyFile

from maya_psyhive.tools.yeti.yeti_viewport import (
    apply_viewport_updates, disable_viewport_updates)
from maya_psyhive.tools.yeti.yeti_read import (
    find_yeti_caches, apply_caches_to_sel_asset,
    apply_caches_in_root_namespace)
from maya_psyhive.tools.yeti.yeti_write import (
    write_cache_from_sel_assets, write_cache_from_sel_yetis,
    write_cache_from_all_yetis)

ICON = icons.EMOJI.find('Ghost')


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
            self.ui.name.redraw)
        self.ui.name.currentTextChanged.connect(
            self.ui.version.redraw)
        self.ui.version.currentIndexChanged.connect(
            self.ui.cache_read_asset.redraw)
        self.ui.version.currentIndexChanged.connect(
            self.ui.cache_read_root.redraw)
        self.ui.version.currentIndexChanged.connect(
            self.ui.version_label.redraw)

    def _redraw__step(self, widget):

        self._yeti_caches = find_yeti_caches(root=self.work.root)

        # Update widget
        _steps = sorted(set([_ver.step for _ver in self._yeti_caches]))
        for _step in _steps:
            widget.add_item(_step)
        if not _steps:
            widget.addItem('<None>')
        widget.setEnabled(bool(_steps))

    def _redraw__name(self, widget):

        _step = self.ui.step.currentText()
        print 'STEP', _step

        _names = sorted(set([_ver.output_name for _ver in self._yeti_caches
                             if _ver.step == _step]))

        # Update widget
        widget.clear()
        for _name in _names:
            widget.add_item(_name)
        if not _names:
            widget.addItem('<None>')
        widget.setEnabled(bool(_names))

        self.ui.version.redraw()

    def _redraw__version(self, widget):

        _step = self.ui.step.currentText()
        _name = self.ui.name.currentText()
        _vers = [_ver for _ver in self._yeti_caches
                 if _ver.step == _step and
                 _ver.output_name == _name]
        print 'STEP/NAME', _step, _name, _vers

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
            _outs = _ver.find_outputs()
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
        write_cache_from_sel_assets(apply_on_complete=_apply_on_complete)

    def _callback__cache_write_assets_help(self):
        _def = PyFile(__file__).find_def(
            write_cache_from_sel_assets.__name__)
        qt.help_(_def.docs)

    def _callback__cache_write_node(self):
        _apply_on_complete = self.ui.apply_on_complete.isChecked()
        write_cache_from_sel_yetis(apply_on_complete=_apply_on_complete)

    def _callback__cache_write_node_help(self):
        _def = PyFile(__file__).find_def(
            write_cache_from_sel_yetis.__name__)
        qt.help_(_def.docs)

    def _callback__cache_write_all_nodes(self):
        _apply_on_complete = self.ui.apply_on_complete.isChecked()
        write_cache_from_all_yetis(apply_on_complete=_apply_on_complete)

    def _callback__cache_write_all_nodes_help(self):
        _def = PyFile(__file__).find_def(
            write_cache_from_all_yetis.__name__)
        qt.help_(_def.docs)

    def _callback__apply_viewport_updates(self):
        apply_viewport_updates()

    def _callback__apply_viewport_updates_help(self):
        _def = PyFile(__file__).find_def(
            apply_viewport_updates.__name__)
        qt.help_(_def.docs)

    def _callback__disable_viewport_updates(self):
        disable_viewport_updates()

    def _callback__disable_viewport_updates_help(self):
        _def = PyFile(__file__).find_def(
            disable_viewport_updates.__name__)
        qt.help_(_def.docs)

    def _callback__cache_read_asset(self):
        _ver = self.ui.version.selected_data()
        _outs = _ver.find_outputs(output_type='yeti', format_='fur')
        apply_caches_to_sel_asset(caches=_outs)

    def _callback__cache_read_asset_help(self):
        _def = PyFile(__file__).find_def(
            apply_caches_to_sel_asset.__name__)
        qt.help_(_def.get_docs().desc_full)

    def _callback__cache_read_root(self):
        _ver = self.ui.version.selected_data()
        _outs = _ver.find_outputs(output_type='yeti', format_='fur')
        apply_caches_in_root_namespace(caches=_outs)

    def _callback__cache_read_root_help(self):
        _def = PyFile(__file__).find_def(
            apply_caches_in_root_namespace.__name__)
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
