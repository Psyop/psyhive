"""Tools for managing reading caches from shotgun."""

from psyhive import qt
from psyhive.utils import lprint


class ShotgunHandler(object):
    """Handler for reading caches from shotgun."""

    hide_omitted = True
    stale_only = True
    cached_shots = set()

    def _read_cache_data(self, shots, progress=True, force=False, dialog=None):
        """Read all cache data.

        Args:
            shots (TTShotRoot list): shots to check
            progress (bool): show progress bar
            force (bool): force reread data from shotgun
            dialog (QDialog): parent dialog
        """
        print 'READING CACHE DATA', force
        _pos = dialog.get_c() if dialog else None
        for _shot in qt.ProgressBar(
                shots, 'Reading {:d} shot{}', col='SeaGreen',
                show=progress, pos=_pos, parent=dialog):
            _shot.read_cache_data(force=force)
            self.cached_shots.add(_shot)

    def _find_cache_data(
            self, shots, steps=None, tasks=None, assets=None,
            hide_omitted=None, stale_only=None, progress=False, force=False,
            dialog=None, verbose=0):
        """Search cache data.

        Args:
            shots (TTShotRoot list): shots to check
            steps (str list): return only data with these steps
            tasks (str list): return only data with these tasks
            assets (TTAssetOutputName list): return only data with these
                asset names
            hide_omitted (bool): ignore omitted caches
            stale_only (bool): ignore caches that used the latest rig/asset
            progress (bool): show progress on read shots
            force (bool): force reread data from shotgun
            dialog (QDialog): parent dialog (for progress bars)
            verbose (int): print process data

        Returns:
            (dict list): filtered cache data
        """
        assert not verbose
        _hide_omitted = (
            self.hide_omitted if hide_omitted is None else hide_omitted)
        _stale_only = (
            self.stale_only if stale_only is None else stale_only)

        if verbose:
            print 'READING CACHE DATA'
            print 'TASKS', tasks
            print 'ASSETS', assets
            print 'STALE ONLY', _stale_only
            print 'HIDE OMITTED', _hide_omitted

        _cache_data = []
        _pos = dialog.ui.get_c() if dialog else None
        for _shot in qt.ProgressBar(
                shots, 'Reading {:d} shots', col='SeaGreen',
                show=progress, pos=_pos):
            if shots and _shot not in shots:
                continue
            for _data in _shot.read_cache_data(force=force):
                _cache = _data['cache']
                _asset_ver = _data['asset_ver']
                _asset = _asset_ver.get_name()
                if _hide_omitted and _data['sg_status_list'] == 'omt':
                    lprint(' - OMITTED REJECT', _cache, verbose=verbose)
                    continue
                if tasks is not None and _cache.task not in tasks:
                    lprint(' - TASK REJECT', _cache, verbose=verbose)
                    continue
                if steps is not None and _cache.step not in steps:
                    lprint(' - STEP REJECT', _cache, verbose=verbose)
                    continue
                if assets is not None and _asset not in assets:
                    lprint(' - ASSET REJECT', _cache, verbose=verbose)
                    continue
                if _stale_only and _asset_ver.is_latest():
                    lprint(' - NOT STALE REJECT', _cache, verbose=verbose)
                    continue
                lprint(
                    ' - ACCEPTED', _cache, _data['origin_scene'],
                    verbose=verbose)
                _cache_data.append(_data)

        return _cache_data

    def find_steps(self, shots, verbose=0):
        """Find steps.

        Args:
            shots (TTShotRoot list): shots to check
            verbose (int): print process data

        Returns:
            (str list): list of matching steps
        """
        _cache_data = self._find_cache_data(shots=shots, verbose=verbose)
        return sorted(set([
            _data['cache'].step for _data in _cache_data]))

    def find_tasks(self, shots, steps):
        """Find tasks.

        Args:
            shots (TTShotRoot list): shots to check
            steps (str list): apply steps filter

        Returns:
            (str list): list of matching tasks
        """
        _cache_data = self._find_cache_data(shots=shots, steps=steps)
        return sorted(set([
            _data['cache'].task for _data in _cache_data]))

    def find_assets(self, shots, steps, tasks):
        """Find available assets.

        Args:
            shots (TTShotRoot list): shots to check
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter

        Returns:
            (TTAssetOutputName list): list of assets
        """
        _cache_data = self._find_cache_data(
            shots=shots, steps=steps, tasks=tasks)
        return sorted(set([
            _data['asset_ver'].get_name() for _data in _cache_data]))

    def find_exports(self, shots=None, steps=None, tasks=None, assets=None):
        """Get list of potential exports.

        Args:
            shots (TTShotRoot list): shots to check
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter
            assets (TTAssetOutputName list): apply asset filter

        Returns:
            (dict): workfile/namespaces
        """
        _cache_data = self._find_cache_data(
            shots=shots, steps=steps, tasks=tasks, assets=assets)
        _exports = {}
        for _data in _cache_data:
            _work_file = _data['work_file']
            _ns = _data['cache'].output_name
            if _work_file not in _exports:
                _exports[_work_file] = []
            if _ns not in _exports[_work_file]:
                _exports[_work_file].append(_ns)
        return _exports

    def find_work_files(self, shots, steps, tasks, cached=None):
        """Find relevant work files.

        Args:
            shots (TTShotRoot list): shots to check
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter
            cached (bool): filter by cached status

        Returns:
            (TTMayaWorkFile list): matching work files
        """
        del cached  # Provided for symmetry
        return self.find_exports(
            shots=shots, steps=steps, tasks=tasks).keys()

    def read_tasks(
            self, shots, force=False, dialog=None, progress=False,
            verbose=0):
        """Read all data required to populate interface.

        Args:
            shots (TTShotRoot list): shots to check
            force (bool): force reread data
            dialog (QDialog): parent dialog
            progress (bool): show progress bar
            verbose (int): print process data
        """
        del verbose  # For lint
        self._read_cache_data(
            shots, force=force, dialog=dialog, progress=progress)
