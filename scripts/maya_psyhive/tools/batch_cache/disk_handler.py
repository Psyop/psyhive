"""Tools for managing reading work file dependencies from disk."""

import copy

from psyhive import tk, qt, pipe
from psyhive.utils import check_heart, lprint, dprint, get_result_storer

from maya_psyhive.tools.batch_cache.tmpl_cache import CTTMayaShotWork


class DiskHandler(object):
    """Handler for reading caches from disk."""

    @get_result_storer(id_as_key=True)
    def _read_work_files(
            self, force=False, confirm=True, dialog=None, verbose=0):
        """Read work files.

        Args:
            force (bool): force reread data
            confirm (bool): show confirmation dialogs
            dialog (QDialog): parent dialog
            verbose (int): print process data

        Returns:
            (CTTMayaShotWork list): work files
        """
        _all_shots = tk.find_shots()

        # Read work files in each shot
        _work_files = []
        _steps = set()
        for _shot in qt.ProgressBar(
                _all_shots, 'Reading {:d} shot{}', col='Thistle',
                parent=dialog):
            for _step in _shot.find_steps():
                _work_area = _step.get_work_area()
                _task_work_files = {}
                for _work_file in _work_area.find_work_files():
                    _task_work_files[_work_file.task] = _work_file
                _work_files += [
                    CTTMayaShotWork(_file.path)
                    for _file in sorted(_task_work_files.values())]
                _steps |= {_work_file.step for _work_file in _work_files}

        if confirm:
            _steps = qt.multi_select(
                msg=(
                    '{:d} latest work files were found in {}.\n\n'
                    'As reading the references of each work file '
                    'can be slow, you may want to ignore some '
                    'steps:'.format(len(_work_files), pipe.cur_project().name)),
                title='Select steps',
                items=sorted(_steps), default=sorted(_steps),
                select='Check work files',
                pos=dialog.get_c() if dialog else None,
                parent=dialog)
            _work_files = [
                _work_file for _work_file in _work_files
                if _work_file.step in _steps]

        # Read work file dependencies
        _force = force
        for _work_file in qt.ProgressBar(
                copy.copy(_work_files), 'Reading {:d} work file{}', col='Plum',
                parent=dialog):

            # Read deps
            check_heart()
            _deps, _replaced_scene = _work_file.read_dependencies(
                confirm=not _force)
            if _replaced_scene:
                _force = True
            lprint('   -', _work_file.basename, _deps, verbose=verbose)
            _assets = _work_file.get_cacheable_assets()
            if not _assets:
                lprint('     - NO CACHEABLE ASSETS', _work_file, verbose=verbose)
                _work_files.remove(_work_file)

        return _work_files

    def find_shots(self):
        """Find shots.

        Returns:
            (TTShotRoot list): list of shots
        """
        return sorted(set([
            _work_file.shot for _work_file in self._read_work_files()]))

    def find_steps(self, shots):
        """Find steps.

        Args:
            shots (TTShotRoot list): apply shots filter

        Returns:
            (str list): list of matching steps
        """
        return sorted(set([
            _work_file.step for _work_file in self._read_work_files()
            if _work_file.shot in shots]))

    def find_tasks(self, shots, steps):
        """Find tasks.

        Args:
            shots (TTShotRoot list): apply shots filter
            steps (str list): apply steps filter

        Returns:
            (str list): list of matching tasks
        """
        return sorted(set([
            _work_file.task for _work_file in self._read_work_files()
            if _work_file.shot in shots and
            _work_file.step in steps]))

    def find_assets(self, shots, steps, tasks):
        """Find available assets.

        Args:
            shots (TTShotRoot list): apply shots filter
            steps (str list): apply steps filter
            tasks (str list): apply tasks filter

        Returns:
            (TTAssetOutputName list): list of assets
        """
        _work_files = sorted([
            _work_file for _work_file in self._read_work_files()
            if _work_file.shot in shots and
            _work_file.step in steps and
            _work_file.task in tasks])

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
        for _work_file in self._read_work_files():
            if (
                    _work_file.shot not in shots or
                    _work_file.step not in steps or
                    _work_file.task not in tasks):
                continue
            lprint('CHECKING REFS', _work_file, verbose=verbose)
            _refs = _work_file.get_cacheable_refs()
            for _ns, _asset in _refs.items():
                if _asset not in assets:
                    continue
                if _work_file not in _exports:
                    _exports[_work_file] = []
                _exports[_work_file.path].append(_ns)

        return _exports

    def read_data(self, confirm=True, force=False, dialog=None, verbose=0):
        """Read all data required to populate interface.

        Args:
            confirm (bool): show confirmation dialogs
            force (bool): force reread data
            dialog (QDialog): parent dialog
            verbose (int): print process data
        """
        _work_files = self._read_work_files(
            force=force, confirm=confirm, dialog=dialog)
        dprint(
            'READ {:d} WORK FILES'.format(len(_work_files)), verbose=verbose)
