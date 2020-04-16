"""Tools for managing reading work file dependencies from disk."""

from psyhive import qt
from psyhive.utils import check_heart, lprint

_COL = 'Plum'


class _Handler(object):
    """Base class for any data handler."""


class DiskHandler(_Handler):
    """Handler for reading caches from disk."""

    cached_shots = set()
    _cached_work_files = set()

    def find_work_files(self, shots, steps=None, tasks=None, cached=None):
        """Find relevant work files in this project.

        Args:
            shots (TTRoot list): filter by shots
            steps (str list): filter by steps
            tasks (str list): filter by tasks
            cached (bool): filter by cached status

        Returns:
            (TTMayaWorkFile list): list of matching work files
        """
        _work_files = []
        for _shot in shots:
            if _shot not in self.cached_shots:
                continue
            for _work_file in _shot.read_work_files():

                if steps is not None and _work_file.step not in steps:
                    continue

                if tasks is not None and _work_file.task not in tasks:
                    continue

                if cached is not None:

                    # Check for unread avaliable cache
                    if _work_file not in self._cached_work_files:
                        if _work_file.has_cache_available():
                            _work_file.read_dependencies()
                            self._cached_work_files.add(_work_file)

                    # Apply cached state filter
                    _is_cached = _work_file in self._cached_work_files
                    if not _is_cached == cached:
                        continue

                _work_files.append(_work_file)

        return _work_files

    def find_steps(self, shots):
        """Find steps.

        Args:
            shots (TTRoot list): apply shots filter

        Returns:
            (str list): list of matching steps
        """
        _work_files = self.find_work_files(shots=shots)
        return sorted(set([_work_file.step for _work_file in _work_files]))

    def find_tasks(self, shots, steps):
        """Find tasks.

        Args:
            shots (TTRoot list): apply shots filter
            steps (str list): apply steps filter

        Returns:
            (str list): list of matching tasks
        """
        _work_files = self.find_work_files(shots=shots, steps=steps)
        return sorted(set([_work_file.task for _work_file in _work_files]))

    def find_assets(self, shots, steps, tasks):
        """Find available assets.

        Args:
            shots (TTRoot list): apply shots filter
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter

        Returns:
            (TTOutputName list): list of assets
        """
        _assets = set()
        for _work_file in self.find_work_files(
                shots=shots, steps=steps, tasks=tasks):
            for _ref in _work_file.get_cacheable_refs():
                _assets.add(_ref)
        return sorted(_assets)

    def find_exports(self, shots, steps, tasks, assets=None, namespaces=None,
                     verbose=0):
        """Get list of potential exports.

        Args:
            shots (TTRoot list): apply shots filter
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter
            assets (str list): apply asset name filter
            namespaces (str list): apply output namespace filter
            verbose (int): print process data

        Returns:
            (dict): workfile/namespaces
        """
        _exports = {}
        for _work_file in self.find_work_files(
                shots=shots, steps=steps, tasks=tasks):
            lprint('CHECKING REFS', _work_file, verbose=verbose)
            _refs = _work_file.get_cacheable_refs()
            for _ns, _asset in _refs.items():
                lprint(' - TESTING', _ns, _asset, verbose=verbose)
                if namespaces and _ns not in namespaces:
                    lprint('   - NS MATCH FAIL', verbose=verbose)
                    continue
                if assets and _asset.asset not in assets:
                    lprint('   - ASSET MATCH FAIL', verbose=verbose)
                    continue
                if _work_file not in _exports:
                    _exports[_work_file] = []
                _exports[_work_file.path].append(_ns)

        return _exports

    def read_tasks(
            self, shots, force=False, dialog=None, progress=False):
        """Read all data required to populate interface.

        Args:
            shots (TTRoot list): shots to check
            force (bool): force reread data
            dialog (QDialog): parent dialog
            progress (bool): show progress bar

        Returns:
            (str list): matching tasks
        """
        for _shot in qt.ProgressBar(
                shots, 'Reading {:d} shot{}', show=progress,
                parent=dialog, col=_COL):
            _shot.read_work_files(force=force)
            self.cached_shots.add(_shot)

    def read_assets(
            self, shots, steps, tasks, force=False, dialog=None,
            verbose=0):
        """Get a list of relevant assets.

        Args:
            shots (TTRoot list): shots to check
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter
            force (bool): force replace current scene with no confirmation
            dialog (QDialog): parent dialog
            verbose (int): print process data

        Returns:
            (CTTAssetOutputVersion list): matching assets
        """
        _work_files = self.find_work_files(
            shots=shots, steps=steps, tasks=tasks, cached=False)
        lprint(
            "READING {:d} WORK FILES".format(len(_work_files)),
            verbose=verbose)

        # Read work file dependencies
        _force = force
        _progress = qt.ProgressBar(
            _work_files, 'Reading {:d} work file{}', col=_COL, parent=dialog)
        for _work_file in _progress:

            check_heart()

            # Read deps
            try:
                _deps, _replaced_scene = _work_file.read_dependencies(
                    confirm=not _force)
            except qt.DialogCancelled:
                _progress.close()
                return None
            if _replaced_scene:
                _force = True
            lprint('   -', _work_file.basename, _deps, verbose=verbose)
            _assets = _work_file.get_cacheable_assets()

            self._cached_work_files.add(_work_file)

        return _work_files


class ShotgunHandler(_Handler):
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
