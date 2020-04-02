"""Tools for managing the batch cache interface."""

import os
import pprint

from psyhive import qt, icons, tk2
from psyhive.tools import get_usage_tracker
from psyhive.utils import dprint, get_plural, lprint

from .bc_disk_handler import DiskHandler
from .bc_sg_handler import ShotgunHandler
from .bc_cache import cache_work_files
from .bc_tmpl_cache import BCRoot

ICON = icons.EMOJI.find('Funeral Urn')


class _BatchCacheUi(qt.HUiDialog3):
    """Interface allow batch caching of work files."""

    def __init__(self, mode=None):
        """Constructor.

        Args:
            mode (str): override read mode (Shotgun/Disk)
        """
        self.mode = mode

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

    def init_ui(self):
        """Init ui elements."""
        if self.mode:
            self.ui.Mode.setCurrentText(self.mode)
        else:
            self._callback__Mode()

        self._callback__hide_omitted()
        self._callback__stale_only()

        self._redraw__Sequences()

    def _redraw__ModeIcon(self):
        _mode = self.ui.Mode.currentText()
        _icon_name = 'Pistol' if _mode == 'Shotgun' else 'Floppy disk'
        _icon = icons.EMOJI.find(_icon_name)
        self.ui.ModeIcon.set_pixmap(_icon)

    def _redraw__ModeInfo(self):
        _mode = self.ui.Mode.currentText()
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
        self.ui.ModeInfo.setText(_text)

    def _redraw__Sequences(self):

        _items = []
        for _seq in tk2.find_sequences():
            _item = qt.HListWidgetItem(_seq.name)
            _item.set_data(_seq)
            _items.append(_item)
        self.ui.Sequences.set_items(_items)

    def _redraw__Shots(self, verbose=0):

        print 'REDRAW SHOTS'

        _seqs = self.ui.Sequences.selected_data()
        _shots = sum([
            _seq.find_shots(class_=BCRoot) for _seq in _seqs], [])
        _handler = self._get_handler()

        lprint('DREW {:d} SHOTS'.format(len(_shots)), verbose=verbose)
        _items = []
        for _shot in sorted(_shots):
            _item = qt.HListWidgetItem(_shot.shot)
            _item.set_data(_shot)
            _col = 'white' if _shot in _handler.cached_shots else 'grey'
            _item.set_col(_col)
            _items.append(_item)
        self.ui.Shots.set_items(_items)

    def _redraw__Steps(self):

        print 'REDRAW STEPS'

        _handler = self._get_handler()
        _shots = self.ui.Shots.selected_data()

        self._uncached_shots = bool([
            _shot for _shot in _shots
            if _shot not in _handler.cached_shots])
        self.ui.Steps.setVisible(not self._uncached_shots)
        self.ui.StepsStale.setVisible(self._uncached_shots)
        self.ui.StepsLayout.setStretch(1, int(self._uncached_shots))
        self.ui.StepsLayout.setStretch(2, int(not self._uncached_shots))
        self.ui.StepsLayout.setStretch(4, int(self._uncached_shots))
        self.ui.StepsLayout.setStretch(5, int(not self._uncached_shots))
        # if self._uncached_shots:
        #     return

        _shots = self.ui.Shots.selected_data()
        _steps = _handler.find_steps(shots=_shots)
        self.ui.Steps.set_items(_steps)

    def _redraw__Tasks(self):

        print 'REDRAW TASKS'

        _handler = self._get_handler()
        _shots = self.ui.Shots.selected_data()
        _steps = self.ui.Steps.selected_text()

        self._uncached_shots = bool([
            _shot for _shot in _shots
            if _shot not in _handler.cached_shots])
        self.ui.Tasks.setVisible(not self._uncached_shots)
        self.ui.TasksStale.setVisible(self._uncached_shots)
        # if self._uncached_shots:
        #     return

        _tasks = self._get_handler().find_tasks(shots=_shots, steps=_steps)
        self.ui.Tasks.set_items(_tasks)

    def _redraw__Assets(self):

        print 'REDRAW ASSETS'

        _handler = self._get_handler()
        _mode = self.ui.Mode.currentText()
        _shots = self.ui.Shots.selected_data()
        _steps = self.ui.Steps.selected_text()
        _tasks = self.ui.Tasks.selected_text()
        _assets_mode = self.ui.AssetsMode.currentText()

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
        self.ui.Assets.setVisible(not self._uncached_work_files)
        self.ui.AssetsStale.setVisible(self._uncached_work_files)

        if self._uncached_work_files:
            _exports = []
        else:
            _exports = _handler.find_exports(
                shots=_shots, steps=_steps, tasks=_tasks)
        _assets = []
        for _namespace, _output in _exports:
            print

        _items = []
        for _asset in _assets:
            _item = qt.HListWidgetItem(_asset)
            _item.set_data(_asset)
            _items.append(_item)
        self.ui.Assets.set_items(_items)

        raise NotImplementedError

    def _redraw__AssetsStale(self):
        _mode = self.ui.Mode.currentText()
        if _mode == 'Disk' and self._uncached_shots:
            _text = 'Refresh steps/tasks\nto update'
        elif _mode == 'Disk':
            _text = 'Refresh assets\nto update'
        else:
            _text = 'Hit refresh to update'
        self.ui.AssetsStale.setText(_text)

    def _redraw__AssetsRefresh(self):
        _mode = self.ui.Mode.currentText()
        self.ui.AssetsRefresh.setEnabled(not self._uncached_shots)
        self.ui.AssetsRefresh.setVisible(_mode == 'Disk')

    def _redraw__Info(self):

        self._exports = []
        self.ui.Info.setVisible(not self._uncached_shots)
        if self._uncached_shots:
            return

        _handler = self._get_handler()
        _shots = self.ui.Shots.selected_data()
        _steps = self.ui.Steps.selected_text()
        _tasks = self.ui.Tasks.selected_text()

        if self._uncached_work_files:
            _work_files = _handler.find_work_files(
                shots=_shots, steps=_steps, tasks=_tasks)
            _uncached_work_files = _handler.find_work_files(
                shots=_shots, steps=_steps, tasks=_tasks, cached=False)
            _text = 'Matched:\n  {:d} work file{}\n  {:d} uncached'.format(
                len(_work_files), get_plural(_work_files),
                len(_uncached_work_files))
        else:
            _assets = self.ui.Assets.selected_data()
            _n_exports = 0
            self._exports = _handler.find_exports(
                shots=_shots, steps=_steps, tasks=_tasks, assets=_assets)
            _n_exports = sum([len(_nss) for _, _nss in self._exports.items()])
            _text = 'Matched:\n  {:d} work file{}\n  {:d} export{}'.format(
                len(self._exports), get_plural(self._exports),
                _n_exports, get_plural(range(_n_exports)))
        self.ui.Info.setText(_text)

    def _redraw__Cache(self):

        self.ui.Cache.setEnabled(bool(self._exports))

    def _callback__Sequences(self):
        self._redraw__Shots()

    def _callback__Shots(self):
        self._redraw__Steps()

    def _callback__Steps(self):
        self._redraw__Tasks()

    def _callback__Tasks(self):
        self._redraw__Assets()

    def _callback__Assets(self):
        self._redraw__Info()

    def _callback__AssetsMode(self):
        self._redraw__Assets()

    def _callback__Mode(self):

        _mode = self.ui.Mode.currentText()
        for _element in [self.ui.HideOmitted, self.ui.StaleOnly]:
            _element.setVisible(_mode == 'Shotgun')
        self._redraw__ModeInfo()
        self._redraw__ModeIcon()

    def _callback__hide_omitted(self):
        _hide_omitted = self.ui.HideOmitted.isChecked()
        self.handlers['Shotgun'].HideOmitted = _hide_omitted
        self._redraw__Shots()

    def _callback__stale_only(self):
        _stale_only = self.ui.StaleOnly.isChecked()
        self.handlers['Shotgun'].StaleOnly = _stale_only
        self._redraw__Shots()

    def _callback__StepsRefresh(self):
        _shots = self.ui.Shots.selected_data()
        self._get_handler().read_tasks(
            shots=_shots, dialog=self, progress=True,
            force=not self._uncached_shots)
        self._redraw__Shots()

    def _callback__AssetsRefresh(self):
        _shots = self.ui.Shots.selected_data()
        _steps = self.ui.Steps.selected_text()
        _tasks = self.ui.Tasks.selected_text()
        self._get_handler().read_assets(
            shots=_shots, tasks=_tasks, steps=_steps, dialog=self, verbose=1)
        self._redraw__Assets()

    def _callback__Cache(self):

        _farm = self.ui.Farm.isChecked()
        _data = self._exports.items()
        pprint.pprint(_data)

        cache_work_files(
            data=_data, farm=_farm, parent=self)

    def _context__Cache(self, menu):

        menu.add_action('Print exports', self._print_exports)

    def _get_handler(self):
        """Get current handler.

        Returns:
            (_Handler): current handler
        """
        _mode = self.ui.Mode.currentText()
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
