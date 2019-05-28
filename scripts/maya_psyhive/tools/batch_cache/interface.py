"""Tools for managing the batch cache interface."""

import os
import pprint

from psyhive import qt, icons, tk
from psyhive.tools import get_usage_tracker
from psyhive.utils import dprint, get_plural, lprint

from maya_psyhive.tools.batch_cache.disk_handler import DiskHandler
from maya_psyhive.tools.batch_cache.sg_handler import ShotgunHandler
from maya_psyhive.tools.batch_cache.cache import cache_work_files
from maya_psyhive.tools.batch_cache.tmpl_cache import CTTShotRoot

ICON = icons.EMOJI.find('Funeral Urn')


class _BatchCacheUi(qt.HUiDialog):
    """Interface allow batch caching of work files."""

    def __init__(self, mode=None):
        """Constructor.

        Args:
            mode (str): override read mode (Shotgun/Disk)
        """
        self._exports = None
        self._uncached_shots = True
        self._uncached_work_files = True
        self.handlers = {
            'Disk': DiskHandler(),
            'Shotgun': ShotgunHandler()}

        # Init ui
        _ui_file = os.path.dirname(__file__)+'/batch_cache.ui'
        super(_BatchCacheUi, self).__init__(ui_file=_ui_file)
        self.setWindowTitle('Batch cache')
        self.set_icon(ICON)

        # Update mode elements
        if mode:
            self.ui.mode.setCurrentText(mode)
        else:
            self.ui.mode.redraw()
        self._callback__hide_omitted()
        self._callback__stale_only()

        # Connect callbacks
        self.ui.mode.currentTextChanged.connect(
            self.ui.mode_info.redraw)
        self.ui.mode.currentTextChanged.connect(
            self.ui.mode_icon.redraw)
        self.ui.mode.currentTextChanged.connect(
            self.ui.shots.redraw)

        self.ui.sequences.itemSelectionChanged.connect(
            self.ui.shots.redraw)
        self.ui.shots.itemSelectionChanged.connect(
            self.ui.steps.redraw)
        self.ui.shots.itemSelectionChanged.connect(
            self.ui.steps.redraw)
        self.ui.steps.itemSelectionChanged.connect(
            self.ui.tasks.redraw)

        self.ui.tasks.itemSelectionChanged.connect(
            self.ui.assets.redraw)
        self.ui.tasks.itemSelectionChanged.connect(
            self.ui.assets_stale.redraw)
        self.ui.tasks.itemSelectionChanged.connect(
            self.ui.assets_refresh.redraw)

        self.ui.assets.itemSelectionChanged.connect(
            self.ui.info.redraw)
        self.ui.assets.itemSelectionChanged.connect(
            self.ui.cache.redraw)

        self.redraw_ui()

    def _redraw__mode_icon(self, widget):
        _mode = self.ui.mode.currentText()
        _icon_name = 'Pistol' if _mode == 'Shotgun' else 'Floppy disk'
        _icon = icons.EMOJI.find(_icon_name)
        widget.set_pixmap(_icon)

    def _redraw__mode_info(self, widget):
        _mode = self.ui.mode.currentText()
        print 'UPDATING MODE INFO', _mode
        if _mode == 'Disk':
            _text = (
                "Assets are found by opening the latest version of each "
                "scene - this can be slow but allows you to cache scenes "
                "that haven't been cached before.")
        elif _mode == 'Shotgun':
            _text = (
                "Assets are read from shotgun - this is fast but you can't "
                "cache scenes that haven't already been cached.")
        else:
            raise ValueError(_mode)
        widget.setText(_text)

    @qt.list_redrawer
    def _redraw__sequences(self, widget):
        _seqs = tk.find_sequences()
        for _seq in _seqs:
            _item = qt.HListWidgetItem(_seq.name)
            _item.set_data(_seq)
            widget.addItem(_item)

    @qt.list_redrawer
    def _redraw__shots(self, widget, verbose=0):
        _seqs = self.ui.sequences.selected_data()
        _shots = sum([
            _seq.find_shots(class_=CTTShotRoot) for _seq in _seqs], [])
        _handler = self._get_handler()

        lprint('DREW {:d} SHOTS'.format(len(_shots)), verbose=verbose)
        for _shot in sorted(_shots):
            _item = qt.HListWidgetItem(_shot.shot)
            _item.set_data(_shot)
            _col = 'white' if _shot in _handler.cached_shots else 'grey'
            _item.set_col(_col)
            widget.addItem(_item)

    @qt.list_redrawer
    def _redraw__steps(self, widget):

        _handler = self._get_handler()
        _shots = self.ui.shots.selected_data()

        self._uncached_shots = bool([
            _shot for _shot in _shots
            if _shot not in _handler.cached_shots])
        widget.setVisible(not self._uncached_shots)
        self.ui.steps_stale.setVisible(self._uncached_shots)
        self.ui.steps_layout.setStretch(1, int(self._uncached_shots))
        self.ui.steps_layout.setStretch(2, int(not self._uncached_shots))
        self.ui.steps_layout.setStretch(4, int(self._uncached_shots))
        self.ui.steps_layout.setStretch(5, int(not self._uncached_shots))
        if self._uncached_shots:
            return

        _shots = self.ui.shots.selected_data()
        _steps = _handler.find_steps(shots=_shots)
        widget.addItems(_steps)

    @qt.list_redrawer
    def _redraw__tasks(self, widget):

        _handler = self._get_handler()
        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()

        self._uncached_shots = bool([
            _shot for _shot in _shots
            if _shot not in _handler.cached_shots])
        widget.setVisible(not self._uncached_shots)
        self.ui.tasks_stale.setVisible(self._uncached_shots)
        if self._uncached_shots:
            return

        _tasks = self._get_handler().find_tasks(shots=_shots, steps=_steps)
        widget.addItems(_tasks)

    @qt.get_list_redrawer(default_selection='all')
    def _redraw__assets(self, widget):
        _handler = self._get_handler()
        _mode = self.ui.mode.currentText()
        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self.ui.tasks.selected_text()
        if _mode == 'Shotgun':
            self._uncached_work_files = self._uncached_shots
        elif _mode == 'Disk':
            if self._uncached_shots:
                self._uncached_work_files = True
            else:
                self._uncached_work_files = bool(_handler.find_work_files(
                    shots=_shots, steps=_steps, tasks=_tasks,
                    cached=False))
        else:
            raise ValueError(_mode)
        widget.setVisible(not self._uncached_work_files)
        self.ui.assets_stale.setVisible(self._uncached_work_files)
        if self._uncached_work_files:
            return

        for _asset in self._get_handler().find_assets(
                shots=_shots, steps=_steps, tasks=_tasks):
            _item = qt.HListWidgetItem(_asset.asset)
            _item.set_data(_asset)
            widget.addItem(_item)

    def _redraw__assets_stale(self, widget):
        _mode = self.ui.mode.currentText()
        if _mode == 'Disk' and self._uncached_shots:
            _text = 'Refresh steps/tasks\nto update'
        elif _mode == 'Disk':
            _text = 'Refresh assets\nto update'
        else:
            _text = 'Hit refresh to update'
        widget.setText(_text)

    def _redraw__assets_refresh(self, widget):
        _mode = self.ui.mode.currentText()
        widget.setEnabled(not self._uncached_shots)
        widget.setVisible(_mode == 'Disk')

    def _redraw__info(self, widget):

        self._exports = []
        widget.setVisible(not self._uncached_shots)
        if self._uncached_shots:
            return

        _handler = self._get_handler()
        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self.ui.tasks.selected_text()

        if self._uncached_work_files:
            _work_files = _handler.find_work_files(
                shots=_shots, steps=_steps, tasks=_tasks)
            _uncached_work_files = _handler.find_work_files(
                shots=_shots, steps=_steps, tasks=_tasks, cached=False)
            _text = 'Matched:\n  {:d} work file{}\n  {:d} uncached'.format(
                len(_work_files), get_plural(_work_files),
                len(_uncached_work_files))
        else:
            _assets = self.ui.assets.selected_data()
            _n_exports = 0
            self._exports = _handler.find_exports(
                shots=_shots, steps=_steps, tasks=_tasks, assets=_assets)
            _n_exports = sum([len(_nss) for _, _nss in self._exports.items()])
            _text = 'Matched:\n  {:d} work file{}\n  {:d} export{}'.format(
                len(self._exports), get_plural(self._exports),
                _n_exports, get_plural(range(_n_exports)))
        widget.setText(_text)

    def _redraw__cache(self, widget):

        widget.setEnabled(bool(self._exports))

    def _callback__mode(self):

        _mode = self.ui.mode.currentText()
        for _element in [self.ui.hide_omitted, self.ui.stale_only]:
            _element.setVisible(_mode == 'Shotgun')

    def _callback__hide_omitted(self):
        _hide_omitted = self.ui.hide_omitted.isChecked()
        self.handlers['Shotgun'].hide_omitted = _hide_omitted
        self.ui.shots.redraw()

    def _callback__stale_only(self):
        _stale_only = self.ui.stale_only.isChecked()
        self.handlers['Shotgun'].stale_only = _stale_only
        self.ui.shots.redraw()

    def _callback__steps_refresh(self):
        _shots = self.ui.shots.selected_data()
        self._get_handler().read_tasks(
            shots=_shots, dialog=self, progress=True,
            force=not self._uncached_shots)
        self.ui.shots.redraw()

    def _callback__assets_refresh(self):
        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self.ui.tasks.selected_text()
        self._get_handler().read_assets(
            shots=_shots, tasks=_tasks, steps=_steps, dialog=self, verbose=1)
        self.ui.assets.redraw()

    def _callback__cache(self):

        _farm = self.ui.farm.isChecked()
        _data = self._exports.items()
        pprint.pprint(_data)

        cache_work_files(
            data=_data, farm=_farm, parent=self)

    def _context__cache(self, menu):

        menu.add_action('Print exports', self._print_exports)

    def _get_handler(self):
        """Get current handler.

        Returns:
            (_Handler): current handler
        """
        _mode = self.ui.mode.currentText()
        return self.handlers[_mode]

    def _print_exports(self):
        """Print exports."""
        print
        dprint('EXPORTS:')
        for _work_file in sorted(self._exports):
            print ' - {:30} {}'.format(
                _work_file.basename, self._exports[_work_file])


@get_usage_tracker(name='launch_batch_cache')
def launch(mode=None):
    """Launch batch cache interface.

    Args:
        mode (str): where to read data from
    """
    from maya_psyhive.tools import batch_cache
    batch_cache.DIALOG = _BatchCacheUi(mode=mode)
    return batch_cache.DIALOG
