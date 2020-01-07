"""Base classes for tank templates work data."""

import copy
import os
import pprint
import shutil
import tempfile
import time

import tank

from psyhive import host, qt
from psyhive.utils import (
    get_single, File, find, dprint, lprint, read_yaml, write_yaml, diff)

from psyhive.tk.templates.tt_base import TTDirBase, TTBase
from psyhive.tk.templates.tt_misc import get_template
from psyhive.tk.misc import find_tank_mod, find_tank_app


class TTWorkAreaBase(TTDirBase):
    """Base class for any work area tank template."""

    work_type = None
    maya_inc_type = None

    def find_increments(self, verbose=0):
        """Find increments belonging to this work area.

        Args:
            verbose (int): print process data

        Returns:
            (TTWorkIncrementBase list): increment files
        """
        _tmp_inc = self.map_to(
            self.maya_inc_type, Task='blah', increment=0, extension='mb',
            version=0)
        lprint('FINDING INCREMENTS', self.maya_inc_type, _tmp_inc,
               verbose=verbose)

        _incs = []
        for _path in find(_tmp_inc.dir, depth=1, type_='f'):
            lprint(' - TESTING PATH', _path)
            try:
                _inc = self.maya_inc_type(_path)
            except ValueError:
                continue
            _incs.append(_inc)

        return _incs

    def find_work_files(self):
        """Find work files in this shot area.

        Returns:
            (TTWorkFileBase list): list of work files
        """
        _work_files = []
        for _file in self.find(depth=2, type_='f'):
            try:
                _work = self.work_type(_file)
            except ValueError:
                continue
            _work_files.append(_work)

        return _work_files

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


class TTWorkFileBase(TTBase, File):
    """Base class for any work file template."""

    output_file_type = None
    output_file_seq_type = None
    output_name_type = None
    output_root_type = None
    output_version_type = None
    step_root_type = None
    task = None
    version = None
    work_area_type = None

    def __init__(self, path, verbose=0):
        """Constructor.

        Args:
            path (str): path to work file
            verbose (int): print process data
        """
        super(TTWorkFileBase, self).__init__(
            path, hint=self.hint, verbose=verbose)
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

    def find_increments(self, verbose=0):
        """Find increments of this work file.

        Args:
            verbose (int): print process data

        Returns:
            (TTWorkIncrementBase list): list of incs
        """
        _area = self.get_work_area()
        lprint('AREA', _area, verbose=verbose)
        _incs = [
            _inc for _inc in _area.find_increments(verbose=verbose)
            if _inc.version == self.version and _inc.task == self.task]
        return _incs

    def find_latest(self, vers=None):
        """Find latest version of this work file stream.

        Args:
            vers (TTWorkFileBase list): override versions list

        Returns:
            (TTWorkFileBase|None): latest version (if any)
        """
        _vers = vers or self.find_vers()
        return _vers[-1] if _vers else None

    def find_next(self, vers=None):
        """Find next version.

        Args:
            vers (TTWorkFileBase list): override versions list

        Returns:
            (TTWorkFileBase): next version
        """
        _data = copy.copy(self.data)
        _latest = self.find_latest(vers=vers)
        _data['version'] = _latest.version + 1 if _latest else 1
        _path = get_template(self.hint).apply_fields(_data)
        return self.__class__(_path)

    def find_output_names(self, filter_=None, verbose=0):
        """Find output names for this work file.

        Args:
            filter_ (str): path filter
            verbose (int): print process data

        Returns:
            (list): list of output names
        """
        _root_tmpl = get_template(self.output_root_type.hint)
        _root = self.output_root_type(_root_tmpl.apply_fields(self.data))
        lprint('ROOT', _root, verbose=verbose)
        _names = []
        for _dir in _root.find(filter_=filter_, depth=2, type_='d'):
            try:
                _name = self.output_name_type(_dir)
            except ValueError:
                continue
            if not _name.task == self.task:
                continue
            lprint(' - ADDED NAME', _name, verbose=verbose)
            _names.append(_name)
        return _names

    def find_outputs(self, filter_=None, verbose=1):
        """Find outputs from this work file.

        Args:
            filter_ (str): path filter
            verbose (int): print process data

        Returns:
            (TTAssetOutputFile list): list of outputs
        """
        _ver_tmpl = get_template(self.output_version_type.hint)

        # Find vers that exist in each name
        lprint('SEARCHING FOR VERSIONS', verbose=verbose)
        _vers = []
        for _name in self.find_output_names(filter_=filter_):
            _data = copy.copy(_name.data)
            _data['version'] = self.version
            _ver = self.output_version_type(_ver_tmpl.apply_fields(_data))
            if _ver.exists():
                lprint(' - ADDED VER', _ver, verbose=verbose)
                _vers.append(_ver)
        lprint('FOUND {:d} VERS'.format(len(_vers)), verbose=verbose)

        # Find output in each ver
        _outputs = []
        for _ver in _vers:
            _ver_outputs = _ver.find_outputs()
            lprint(' -', _ver, len(_ver_outputs), _ver_outputs,
                   verbose=verbose)
            _outputs += _ver_outputs

        return _outputs

    def find_vers(self):
        """Find other versions of this workfile.

        Returns:
            (TTWorkFileBase list): versions
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

    def get_step_root(self):
        """Get step root for this work file.

        Returns:
            (TTStepRootBase): step root
        """
        return self.step_root_type(self.path)

    def get_work_area(self):
        """Get work area associated with this work file.

        Returns:
            (TTWorkAreaBase): work area
        """
        return self.work_area_type(self.path)

    def load(self, force=True):
        """Load this work file.

        Args:
            force (bool): open with no scene modified warning
        """
        from psyhive import tk
        _fileops = tk.find_tank_app('psy-multi-fileops')
        _fileops.open_file(self.path, force=force)
        self.update_output_paths(catch=True)

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

    def update_output_paths(self, catch=False):
        """Update current scene output paths to match this work file.

        Args:
            catch (bool): no error if update output file paths fails
        """
        from psyhive import tk
        if os.environ.get('PSYHIVE_DISABLE_UPDATE_OUTPUT_PATHS'):
            print 'UPDATE OUTPUT PATHS DISABLED'
            return

        # Make sure outputpaths app is loaded
        _engine = tank.platform.current_engine()
        _tk = tank.Sgtk(self.path)
        _ctx = _tk.context_from_path(self.path)
        try:
            _engine.change_context(_ctx)
        except tank.TankError as _exc:
            if not catch:
                raise _exc
            print 'FAILED TO APPLY CONTEXT', _ctx
            return

        # Apply output paths
        _outputpaths = tk.find_tank_app('outputpaths')
        _no_workspace = not host.cur_scene()
        try:
            _outputpaths.update_output_paths(
                scene_path=self.path, no_workspace=_no_workspace)
        except AttributeError as _exc:
            if not catch:
                raise _exc
            print 'FAILED TO UPDATE OUTPUT PATHS'


class TTWorkIncrementBase(TTBase, File):
    """Base class for any tank template increment file."""

    maya_work_type = None

    def get_work(self):
        """Get work file this increment belongs to.

        Returns:
            (TTWorkFileBase): work file
        """
        _class = self.maya_work_type
        return self.map_to(_class)

    def load(self):
        """Load this work file."""
        _engine = tank.platform.current_engine()
        _fileops = _engine.apps['psy-multi-fileops']
        _work_file = _fileops.get_workfile_from_path(self.path)
        _fileops.open_file(
            _work_file, open=True, force=True, change_context=True)
