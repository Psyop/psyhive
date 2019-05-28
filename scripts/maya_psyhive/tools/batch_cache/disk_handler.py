"""Tools for managing reading work file dependencies from disk."""

from psyhive import qt
from psyhive.utils import check_heart, lprint

_COL = 'Plum'


class DiskHandler(object):
    """Handler for reading caches from disk."""

    cached_shots = set()
    _cached_work_files = set()

    def find_work_files(self, shots, steps=None, tasks=None, cached=None):
        """Find relevant work files in this project.

        Args:
            shots (TTShotRoot list): filter by shots
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
            shots (TTShotRoot list): apply shots filter

        Returns:
            (str list): list of matching steps
        """
        _work_files = self.find_work_files(shots=shots)
        return sorted(set([_work_file.step for _work_file in _work_files]))

    def find_tasks(self, shots, steps):
        """Find tasks.

        Args:
            shots (TTShotRoot list): apply shots filter
            steps (str list): apply steps filter

        Returns:
            (str list): list of matching tasks
        """
        _work_files = self.find_work_files(shots=shots, steps=steps)
        return sorted(set([_work_file.task for _work_file in _work_files]))

    def find_assets(self, shots, steps, tasks):
        """Find available assets.

        Args:
            shots (TTShotRoot list): apply shots filter
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter

        Returns:
            (TTAssetOutputName list): list of assets
        """
        _work_files = self.find_work_files(
            shots=shots, steps=steps, tasks=tasks)
        return sorted(set(sum([
            _work_file.get_cacheable_assets()
            for _work_file in _work_files], [])))

    def find_exports(self, shots, steps, tasks, assets, verbose=0):
        """Get list of potential exports.

        Args:
            shots (TTShotRoot list): apply shots filter
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter
            assets (TTAssetOutputName list): apply asset filter
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
                if _asset not in assets:
                    continue
                if _work_file not in _exports:
                    _exports[_work_file] = []
                _exports[_work_file.path].append(_ns)

        return _exports

    def read_tasks(
            self, shots, force=False, dialog=None, progress=False):
        """Read all data required to populate interface.

        Args:
            shots (TTShotRoot list): shots to check
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
            shots (TTShotRoot list): shots to check
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
        for _work_file in qt.ProgressBar(
                _work_files, 'Reading {:d} work file{}', col=_COL,
                parent=dialog):

            # Read deps
            check_heart()
            _deps, _replaced_scene = _work_file.read_dependencies(
                confirm=not _force)
            if _replaced_scene:
                _force = True
            lprint('   -', _work_file.basename, _deps, verbose=verbose)
            _assets = _work_file.get_cacheable_assets()

            self._cached_work_files.add(_work_file)

        return _work_files
