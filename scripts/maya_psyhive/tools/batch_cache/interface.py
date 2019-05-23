"""Tools for managing the batch cache interface."""

import os
import pprint

from psyhive import qt, icons
from psyhive.tools import get_usage_tracker
from psyhive.utils import dprint

from maya_psyhive.tools.batch_cache.disk_handler import DiskHandler
from maya_psyhive.tools.batch_cache.sg_handler import ShotgunHandler
from maya_psyhive.tools.batch_cache.cache import cache_work_files

ICON = icons.EMOJI.find('Funeral Urn')
_DIALOG = None


class _BatchCacheUi(qt.HUiDialog):
    """Interface allow batch caching of work files."""

    def __init__(self, mode='Shotgun', confirm=True):
        """Constructor.

        Args:
            mode (str): where to read data from
            confirm (bool): show confirmation dialogs
        """
        self._exports = None

        # Set up handler
        self.handlers = {
            'Disk': DiskHandler(),
            'Shotgun': ShotgunHandler()}
        self.handlers[mode].read_data(confirm=confirm, verbose=1)

        # # Init ui
        _ui_file = os.path.dirname(__file__)+'/batch_cache.ui'
        super(_BatchCacheUi, self).__init__(
            ui_file=_ui_file, connect_widgets=False,
            show=False)
        self.setWindowTitle('Batch cache')
        self.ui.mode.setCurrentText(mode)
        self._callback__mode()
        self._callback__hide_omitted()
        self._callback__stale_only()
        self.connect_widgets(verbose=1)
        self.set_icon(ICON)

        self.ui.mode.currentTextChanged.connect(
            self.ui.mode_info.redraw)
        self.ui.mode.currentTextChanged.connect(
            self.ui.shots.redraw)
        self.ui.shots.itemSelectionChanged.connect(
            self.ui.steps.redraw)
        self.ui.steps.itemSelectionChanged.connect(
            self.ui.tasks.redraw)
        self.ui.tasks.itemSelectionChanged.connect(
            self.ui.assets.redraw)
        self.ui.assets.itemSelectionChanged.connect(
            self.ui.info.redraw)

        self.redraw_ui()
        self.ui.show()

    def _redraw__mode_info(self, widget):

        self._get_handler().read_data(dialog=self)
        _mode = self.ui.mode.currentText()
        print 'UPDATING MODE INFO', _mode
        if _mode == 'Disk':
            _text = (
                'Assets found by opening the latest version of each scene')
        elif _mode == 'Shotgun':
            _text = 'Assets read from shotgun'
        else:
            raise ValueError(_mode)
        widget.setText(_text)

    @qt.get_list_redrawer(default_selection='all')
    def _redraw__shots(self, widget):

        _shots = self._get_handler().find_shots()
        print 'DREW', len(_shots), 'SHOTS'
        for _shot in sorted(_shots):
            _item = qt.HListWidgetItem(_shot.shot)
            _item.set_data(_shot)
            widget.addItem(_item)
        widget.selectAll()

    @qt.get_list_redrawer(default_selection='all')
    def _redraw__steps(self, widget):

        _shots = self.ui.shots.selected_data()
        _steps = self._get_handler().find_steps(shots=_shots)
        widget.addItems(_steps)

    @qt.get_list_redrawer(default_selection='all')
    def _redraw__tasks(self, widget):

        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self._get_handler().find_tasks(shots=_shots, steps=_steps)
        widget.addItems(_tasks)

    @qt.get_list_redrawer(default_selection='all')
    def _redraw__assets(self, widget):

        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self.ui.tasks.selected_text()

        for _asset in self._get_handler().find_assets(
                shots=_shots, steps=_steps, tasks=_tasks):
            _item = qt.HListWidgetItem(_asset.asset)
            _item.set_data(_asset)
            widget.addItem(_item)

    def _redraw__info(self, widget):

        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self.ui.tasks.selected_text()
        _assets = self.ui.assets.selected_data()

        _n_exports = 0
        self._exports = self._get_handler().find_exports(
            shots=_shots, steps=_steps, tasks=_tasks, assets=_assets)
        _n_exports = sum([len(_nss) for _, _nss in self._exports.items()])

        widget.setText(
            'Matched:\n  {:d} exports\n  {:d} work files'.format(
                _n_exports, len(self._exports)))

    def _callback__mode(self):

        _mode = self.ui.mode.currentText()
        for _element in [self.ui.hide_omitted, self.ui.stale_only]:
            _element.setVisible(_mode == 'Shotgun')

    def _callback__hide_omitted(self):
        _hide_omitted = self.ui.hide_omitted.isChecked()
        self.handlers['Shotgun'].hide_omitted = _hide_omitted
        self._redraw__shots(self.ui.shots)

    def _callback__stale_only(self):
        _stale_only = self.ui.stale_only.isChecked()
        self.handlers['Shotgun'].stale_only = _stale_only
        self._redraw__shots(self.ui.shots)

    def _callback__cache(self):

        _farm = self.ui.farm.isChecked()
        _data = self._exports.items()
        pprint.pprint(_data)

        cache_work_files(
            data=_data, farm=_farm, parent=self)

    def _callback__refresh(self):
        self._get_handler().read_data(force=True, dialog=self)
        self._redraw__shots(self.ui.shots)

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
def launch(mode=None, confirm=True):
    """Launch batch cache interface.

    Args:
        mode (str): where to read data from
        confirm (bool): show confirmation dialogs
    """
    global _DIALOG

    _mode = mode or qt.raise_dialog(
        'Which scenes do you want to cache?\n\n'
        'Reading from shotgun is quicker, but you can only cache scenes '
        'that have already been cached.\n\n'
        'Reading from disk is slower but allows you to cache scenes '
        'which haven\'t been cached before.',
        title='Select mode',
        icon=icons.EMOJI.find("Funeral urn"),
        buttons=["Shotgun", "Disk", "Cancel"])

    _DIALOG = _BatchCacheUi(mode=_mode, confirm=confirm)
    return _DIALOG
