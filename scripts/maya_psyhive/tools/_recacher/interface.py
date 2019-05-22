"""Interface for recacher tool."""

import os

from psyhive import qt, pipe, icons
from psyhive.tools import catch_error, get_usage_tracker

from psyhive.utils import abs_path, dprint, get_plural, lprint, wrap_fn

from maya_psyhive.tools.recacher.misc import CacheDataShot
from maya_psyhive.tools.recacher.cache import cache_work_files

ICON = icons.EMOJI.find('Flower Playing Cards')


class _RecacherUi(qt.HUiDialog):
    """Interface for recaching a shot."""

    def __init__(self):
        """Constructor."""
        self.shots = [
            CacheDataShot(_shot.path)
            for _shot in pipe.cur_project().find_shots()]
        self.find_cache_data(
            progress=True, hide_omitted=False, stale_only=False)

        _ui_file = abs_path("recacher.ui", root=os.path.dirname(__file__))
        super(_RecacherUi, self).__init__(ui_file=_ui_file)
        self.set_icon(ICON)

        self.ui.stale_only.stateChanged.connect(self.ui.shots.redraw)
        self.ui.hide_omitted.stateChanged.connect(self.ui.shots.redraw)
        self.ui.shots.itemSelectionChanged.connect(self.ui.steps.redraw)
        self.ui.steps.itemSelectionChanged.connect(self.ui.tasks.redraw)
        self.ui.tasks.itemSelectionChanged.connect(self.ui.assets.redraw)
        self.ui.assets.itemSelectionChanged.connect(self.ui.info.redraw)
        self.ui.assets.itemSelectionChanged.connect(self.ui.recache.redraw)

        _omit = self.ui.hide_omitted.isChecked()
        self.ui.hide_omitted.stateChanged.emit(_omit)

    def _redraw__shots(self, widget):

        dprint('REDRAW SHOTS')
        _sel = widget.selected_text()
        widget.clear()
        for _shot in self.shots:
            _shot = CacheDataShot(_shot.path)
            _item = qt.HListWidgetItem(_shot.name)
            _item.set_data(_shot)
            widget.addItem(_item)

        if _sel:
            widget.select_text(_sel)
        else:
            widget.selectAll()

    def _redraw__steps(self, widget):

        dprint('REDRAW STEPS')

        _shots = self.ui.shots.selected_data()
        _cache_data = self.find_cache_data(shots=_shots)
        _steps = sorted(set([
            _data['cache'].step for _data in _cache_data]))
        widget.clear()
        widget.addItems(_steps)

        widget.selectAll()

    def _redraw__tasks(self, widget):

        dprint('REDRAW TASKS')

        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _cache_data = self.find_cache_data(shots=_shots, steps=_steps)
        _tasks = sorted(set([
            _data['cache'].task for _data in _cache_data]))
        widget.clear()
        widget.addItems(_tasks)
        widget.selectAll()

    def _redraw__assets(self, widget):

        dprint('REDRAW CACHED ASSETS')

        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self.ui.tasks.selected_text()

        _cache_data = self.find_cache_data(
            shots=_shots, steps=_steps, tasks=_tasks)
        _asset_names = sorted(set([
            _data['asset'].asset for _data in _cache_data]))
        widget.clear()
        widget.addItems(_asset_names)
        widget.selectAll()

    def _redraw__info(self, widget):

        _data = self._get_recache_data()
        _work_files = sorted(set([
            _item['work_file'].ver_fmt for _item in _data]))
        _caches = sorted(set([_item['cache'] for _item in _data]))
        _text = 'Matched:\n  {:d} cache{}\n  {:d} work file{}'.format(
            len(_caches), get_plural(_caches),
            len(_work_files), get_plural(_work_files))

        widget.setText(_text)

    def _redraw__recache(self, widget):

        widget.setEnabled(bool(self._get_recache_data()))

    def _callback__recache(self, execute=True):

        _farm = self.ui.farm.isChecked()
        _recache = {}
        _cache_data = self._get_recache_data()
        _caches_items = [
            (_item['cache'], _item['asset'], _item['work_file'])
            for _item in _cache_data]

        for _shot in self.ui.shots.selected_data():

            # Get list of selected caches
            _shot_items = [
                _item for _item in _caches_items if _item[0].shot == _shot]

            # Print versions to recache
            print
            print _shot.name
            for _cache, _asset, _work_file in _shot_items:
                print ' - {:25} {:15} {:15} {:15} {:30} {:50} {}'.format(
                    _cache.output_name,
                    _work_file.step,
                    _work_file.task,
                    'v{:03d}'.format(_asset.version),
                    _asset.get_status(),
                    _shot.rel_path(_cache.path),
                    _work_file.filename)
                if _work_file.ver_fmt not in _recache:
                    _latest_work = _work_file.find_vers()[-1]
                    _recache[_work_file.ver_fmt] = _latest_work, set()
                _recache[_work_file.ver_fmt][1].add(_cache.output_name)

        if not execute:
            return

        cache_work_files(
            [_recache[_ver_fmt] for _ver_fmt in sorted(_recache)],
            farm=_farm, parent=self)

        self._callback__refresh()

    def _callback__refresh(self):

        self.find_cache_data(progress=True, force=True)
        self.redraw_ui()

    def _context__recache(self, menu):

        menu.addAction(
            'Print matches',
            wrap_fn(self._callback__recache, execute=False))

    def find_cache_data(
            self, shots=None, steps=None, tasks=None, assets=None,
            hide_omitted=None, stale_only=None, progress=False, force=False,
            verbose=0):
        """Search cache data.

        Args:
            shots (Shot list): return only data from these shots
            steps (str list): return only data with these steps
            tasks (str list): return only data with these tasks
            assets (str list): return only data with these asset names
            hide_omitted (bool): ignore omitted caches
            stale_only (bool): ignore caches that used the latest rig/asset
            progress (bool): show progress on read shots
            force (bool): force reread data from shotgun
            verbose (int): print process data

        Returns:
            (dict list): filtered cache data
        """
        _hide_omitted = (
            self.ui.hide_omitted.isChecked() if hide_omitted is None
            else hide_omitted)
        _stale_only = (
            self.ui.stale_only.isChecked() if stale_only is None
            else stale_only)

        if verbose:
            print 'READING CACHE DATA'
            print 'TASKS', tasks
            print 'ASSETS', assets

        _cache_data = []
        _pos = self.get_c() if hasattr(self, 'ui') else None
        for _shot in qt.ProgressBar(
                self.shots, 'Reading {:d} shots', col='SeaGreen',
                show=progress, pos=_pos):
            if shots and _shot not in shots:
                continue
            for _data in _shot.read_cache_data(force=force):
                _cache = _data['cache']
                _asset = _data['asset']
                if _hide_omitted and _data['sg_status_list'] == 'omt':
                    continue
                if tasks is not None and _cache.task not in tasks:
                    lprint(' - TASK REJECT', _cache, verbose=verbose)
                    continue
                if steps is not None and _cache.step not in steps:
                    continue
                if assets is not None and _asset.asset not in assets:
                    continue
                if _stale_only and _asset.is_latest():
                    continue
                lprint(
                    ' - ACCEPTED', _cache, _data['origin_scene'],
                    verbose=verbose)
                _cache_data.append(_data)

        return _cache_data

    def _get_recache_data(self, verbose=0):
        """Get list of recaches based on the current settings.

        Args:
            verbose (int): print process data

        Returns:
            (dict list): filtered cache data
        """
        _shots = self.ui.shots.selected_data()
        _steps = self.ui.steps.selected_text()
        _tasks = self.ui.tasks.selected_text()
        _assets = self.ui.assets.selected_text()

        return self.find_cache_data(
            shots=_shots, steps=_steps, tasks=_tasks, assets=_assets,
            verbose=verbose)


@catch_error
@get_usage_tracker(name='launch_fkik_switcher')
def launch():
    """Launch RecacherUi interface."""
    from maya_psyhive.tools import recacher
    recacher.DIALOG = _RecacherUi()
    return recacher.DIALOG
