"""Tools for managing work tank template representations."""

import copy
import os
import pprint
import shutil
import tempfile
import time

from psyhive import qt, host
from psyhive.utils import (
    File, abs_path, lprint, find, dprint, read_yaml, get_single,
    write_yaml, diff)

from psyhive.tk2.tk_utils import find_tank_app, find_tank_mod
from psyhive.tk2.tk_templates.tt_base import (
    TTDirBase, TTBase, TTStepRoot, TTRoot)
from psyhive.tk2.tk_templates.tt_utils import (
    get_area, get_dcc, get_template, get_extn)


class TTWorkArea(TTDirBase):
    """Represents a work area within a step root for a dcc."""

    hint_fmt = '{area}_work_area_{dcc}'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to work area
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _dcc = get_dcc(_path)
        _hint = self.hint_fmt.format(area=_area, dcc=_dcc)
        super(TTWorkArea, self).__init__(path, hint=_hint)

    def find_increments(self):
        """Find increments belonging to this work area.

        Returns:
            (TTIncrement list): increment files
        """
        _hint = '{}_{}_increment'.format(self.dcc, self.area)
        _tmp_inc = self.map_to(
            hint=_hint, class_=TTIncrement, Task='blah', increment=0,
            extension=get_extn(self.dcc), version=0)
        return find(_tmp_inc.dir, depth=1, type_='f', class_=TTIncrement)

    def find_work(self, class_=None):
        """Find work files in this shot area.

        Args:
            class_ (class): override work file class

        Returns:
            (TTWork list): list of work files
        """
        _class = class_ or TTWork
        _hint = '{}_{}_work'.format(self.dcc, self.area)
        _tmpl = get_template(_hint)
        _test_work = self.map_to(
            hint=_hint, class_=_class, Task=self.step,
            extension=get_extn(self.dcc), version=1)
        _works = find(_test_work.dir, depth=1, type_='f', class_=_class)
        return _works

    def get_metadata(self, verbose=1):
        """Read this work area's metadata yaml file.

        Args:
            verbose (int): print process data

        Returns:
            (dict): work area metadata
        """
        dprint("Reading metadata", self.path, verbose=verbose)
        if not os.path.exists(self.yaml):
            return {}
        return read_yaml(self.yaml)

    def set_metadata(self, data):
        """Set metadata for this work area, writing yaml to disk.

        Args:
            data (dict): metadata to write
        """
        assert len(data['workfiles']) == len(self.get_metadata()['workfiles'])
        _tmp_yaml = '{}/metadata.yaml'.format(tempfile.gettempdir())
        write_yaml(data=data, file_=_tmp_yaml)
        if not os.path.getsize(self.yaml) - 20 < os.path.getsize(_tmp_yaml):
            print os.path.getsize(self.yaml), self.yaml
            print os.path.getsize(_tmp_yaml), _tmp_yaml
            diff(_tmp_yaml, self.yaml)
            raise ValueError("Losing data")
        shutil.copy(_tmp_yaml, self.yaml)

    @property
    def yaml(self):
        """Stores path to this work area's metadata yaml file."""
        return '{}/metadata.yml'.format(self.path)


class TTWork(TTBase, File):
    """Represents a work file."""

    task = None
    version = None

    hint_fmt = '{dcc}_{area}_work'

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to work file
        """
        File.__init__(self, file_)

        # Get hint
        _path = abs_path(file_)
        _dcc = get_dcc(_path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(dcc=_dcc, area=_area)

        super(TTWork, self).__init__(file_, hint=_hint)

        self.ver_fmt = '{}/{}'.format(
            self.dir, self.filename.replace(
                '_v{:03d}'.format(self.version), '_v{:03d}'))

    def add_to_recent(self):
        """Add this file to tank recent file list for this show."""
        _fileops = find_tank_app('psy-multi-fileops')
        _mod = find_tank_mod('workspace', app='psy-multi-fileops')
        _tk_workspace = _mod.get_workspace_from_path(
            app=_fileops, path=self.path)
        _tk_workfile = _mod.WorkfileModel(
            workspace=_tk_workspace, template=self.tmpl,
            path=self.path)
        _tk_workfile._modified_time = time.time()
        _fileops.user_settings.add_workfile_to_recent_settings(_tk_workfile)

    def find_caches(self):
        """Find caches associated with this work file.

        Returns:
            (TTOutput list): list of caches
        """
        return [
            _output for _output in self.find_outputs()
            if _output.output_type in ('camcache', 'animcache')]

    def find_captures(self):
        """Find captures associated with this work file.

        Returns:
            (TTOutput list): list of captures
        """
        return self.find_outputs(output_type='capture')

    def find_increments(self, verbose=0):
        """Find increments of this work file.

        Args:
            verbose (int): print process data

        Returns:
            (TTIncrement list): list of incs
        """
        _area = self.get_work_area()
        lprint('AREA', _area, verbose=verbose)
        _incs = [
            _inc for _inc in _area.find_increments()
            if _inc.version == self.version and _inc.task == self.task]
        return _incs

    def find_latest(self, vers=None):
        """Find latest version of this work file stream.

        Args:
            vers (TTWork list): override versions list

        Returns:
            (TTWork|None): latest version (if any)
        """
        _vers = vers or self.find_vers()
        return _vers[-1] if _vers else None

    def find_next(self, vers=None):
        """Find next version.

        Args:
            vers (TTWork list): override versions list

        Returns:
            (TTWork): next version
        """
        _data = copy.copy(self.data)
        _latest = self.find_latest(vers=vers)
        _data['version'] = _latest.version + 1 if _latest else 1
        _path = get_template(self.hint).apply_fields(_data)
        return self.__class__(_path)

    def find_outputs(self, filter_=None, output_type=None):
        """Find outputs from this work file.

        Args:
            filter_ (str): path filter
            output_type (str): filter by output type

        Returns:
            (TTOutput list): list of outputs
        """
        return self.get_step_root().find_outputs(
            task=self.task, version=self.version, filter_=filter_,
            output_type=output_type)

    def find_output_files(self, verbose=0):
        """Find output files associated with this work file.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutput list): list of outputs
        """
        return sum([_out.find_files(verbose=verbose)
                    for _out in self.find_outputs()], [])

    def find_publishes(self):
        """Find publishes associated with this work file.

        Returns:
            (TTOutput list): list of publishes
        """
        return [_output for _output in self.find_outputs()
                if _output.output_type in ('rig', 'shadegeo')]

    def find_renders(self):
        """Find renders associated with this work file.

        Returns:
            (TTOutput list): list of renders
        """
        return self.find_outputs(output_type='render')

    def find_seqs(self):
        """Find sequences associated with this work file.

        Returns:
            (TTOutput list): list of sequences
        """
        return [_output for _output in self.find_outputs()
                if _output.output_type in ('render', 'capture')]

    def find_vers(self):
        """Find other versions of this workfile.

        Returns:
            (TTWork list): versions
        """
        _vers = []
        for _file in find(self.dir, extn=self.extn, type_='f', depth=1):
            try:
                _work = self.__class__(_file)
            except ValueError:
                continue
            if not _work.task == self.task:
                continue
            _vers.append(_work)
        return _vers

    def get_comment(self, verbose=1):
        """Get this work file's comment.

        Args:
            verbose (int): print process data

        Returns:
            (str): comment
        """
        return self.get_metadata(verbose=verbose).get('comment')

    def get_metadata(self, data=None, catch=True, verbose=0):
        """Get metadata for this work file.

        This can be expensive - it should read at work area level and
        then passed using the data arg.

        Args:
            data (dict): override data dict rather than read from disk
            catch (bool): no error on work file missing from metadata
            verbose (int): print process data
        """
        dprint('Reading metadata', self.path, verbose=verbose)
        _work_area = self.get_work_area()
        if data:
            _data = data
        else:
            dprint(
                'Reading work area metadata (slow)', _work_area.path,
                verbose=verbose)
            _data = _work_area.get_metadata()
        if not _data:
            return {}

        # Apply task filter
        _task_files = [
            _data for _data in _data['workfiles']
            if _data['name'] == self.task.lower()]
        if not _task_files:
            if catch:
                return {}
            raise ValueError('Missing task {} from metadata {}'.format(
                self.task.lower(), self.path))
        _work_files = get_single(_task_files)
        lprint(
            "MATCHED {:d} WORK FILES IN TASK {}".format(
                len(_work_files), self.task.lower()),
            verbose=verbose > 1)
        lprint(pprint.pformat(_work_files), verbose=verbose > 1)

        # Find this version
        if 'versions' not in _work_files:
            raise ValueError(
                "Missing versions key in metadata "+_work_area.path)
        _versions = [
            _data for _data in _work_files['versions']
            if _data['version'] == self.version]
        if not _versions and catch:
            return {}
        _version = get_single(
            _versions, fail_message='Missing version in metadata '+self.path)

        return _version

    def get_shot(self):
        """Get this work file's shot.

        Returns:
            (TTRoot|None): shot (if any)
        """
        if self.shot:
            return TTRoot(self.path)
        return None

    def get_step_root(self):
        """Get step root for this work file.

        Returns:
            (TTStepRoot): step root
        """
        return TTStepRoot(self.path)

    def get_work_area(self):
        """Get work area associated with this work file.

        Returns:
            (TTWorkArea): work area
        """
        return TTWorkArea(self.path)

    def load(self, force=True):
        """Load this work file.

        Args:
            force (bool): open with no scene modified warning
        """
        _fileops = find_tank_app('psy-multi-fileops')
        _fileops.open_file(self.path, force=force)

    def save(self, comment):
        """Save this version.

        Args:
            comment (str): comment for version
        """
        _fileops = find_tank_app('psy-multi-fileops')
        _mod = find_tank_mod('workspace', app='psy-multi-fileops')
        _prev = self.find_latest()

        if self.exists():

            self._save_inc(comment=comment)

        else:

            # Get prev workfile
            if _prev:
                assert _prev.version == self.version - 1
                _tk_workspace = _mod.get_workspace_from_path(
                    app=_fileops, path=_prev.path)
                _tk_workfile = _mod.WorkfileModel(
                    workspace=_tk_workspace, template=_prev.tmpl,
                    path=_prev.path)
                _tk_workfile = _tk_workfile.get_next_version()
            else:
                assert self.version == 1
                _tk_workspace = _mod.get_workspace_from_path(
                    app=_fileops, path=self.path)
                _tk_workfile = _tk_workspace.get_workfile(
                    name=self.task, version=1)

            _tk_workfile.save()

        # Save metadata
        qt.get_application().processEvents()
        self.set_comment(comment)
        self.add_to_recent()

    def _save_inc(self, comment):
        """Save increment file.

        Args:
            comment (str): comment
        """
        assert host.cur_scene() == self.path
        _fileops = find_tank_app('psy-multi-fileops')
        _fileops.save_increment_file(comment=comment)

    def set_comment(self, comment):
        """Set comment for this version.

        Args:
            comment (str): comment to apply
        """
        _fileops = find_tank_app('psy-multi-fileops')
        _mod = find_tank_mod('workspace', app='psy-multi-fileops')

        _tk_workspace = _mod.get_workspace_from_path(
            app=_fileops, path=self.path)
        _tk_workfile = _tk_workspace.get_workfile(
            name=self.task, version=self.version)
        _tk_workfile.metadata.comment = comment
        _tk_workfile.metadata.save()


class TTIncrement(TTBase, File):
    """Represents a work file increment."""

    hint_fmt = '{dcc}_{area}_increment'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to increment file
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _dcc = get_dcc(_path)
        _hint = self.hint_fmt.format(dcc=_dcc, area=_area)
        super(TTIncrement, self).__init__(path, hint=_hint)
