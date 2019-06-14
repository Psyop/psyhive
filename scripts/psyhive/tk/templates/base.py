"""Tools for accessing tank pipeline data."""

import copy
import os
import pprint
import tempfile
import shutil

import tank

from tank.platform import current_engine

from psyhive import pipe, host
from psyhive.utils import (
    get_single, Dir, File, abs_path, find, Path, dprint,
    lprint, read_yaml, write_yaml, diff)

from psyhive.tk.templates.misc import get_template
from psyhive.tk.misc import find_tank_mod


class TTBase(Path):
    """Base class for any tank template object."""

    step = None
    hint = None

    def __init__(
            self, path, hint=None, tmpl=None, data=None, verbose=0):
        """Constructor.

        Args:
            path (str): path to object
            hint (str): template name
            tmpl (TemplatePath): override template object
            data (dict): override data dict
            verbose (int): print process data
        """
        _path = abs_path(path)
        lprint('PATH', _path, verbose=verbose)
        super(TTBase, self).__init__(_path)
        self.hint = hint or self.hint
        self.tmpl = tmpl or current_engine().tank.templates[self.hint]

        self.project = pipe.Project(path)
        if self.project != pipe.cur_project():
            raise ValueError('Not current project '+self.path)

        try:
            self.data = data or self.tmpl.get_fields(self.path)
        except tank.TankError as _exc:
            lprint('TANK ERROR', _exc.message, verbose=verbose)
            raise ValueError("Tank rejected {} {}".format(
                self.hint, self.path))
        lprint('DATA', pprint.pformat(self.data), verbose=verbose)
        for _key, _val in self.data.items():
            _key = _key.lower()
            if getattr(self, _key, None) is not None:
                continue
            setattr(self, _key, _val)


class TTDirBase(Dir, TTBase):
    """Base class for any tank template directoy object."""

    def __init__(self, path, hint=None, verbose=0):
        """Constructor.

        Args:
            path (str): path to object
            hint (str): template name
            verbose (int): print process data
        """
        _raw_path = abs_path(path)
        _hint = hint or self.hint
        _tmpl = current_engine().tank.templates[_hint]
        _def = abs_path(_tmpl.definition, root=pipe.Project(path).path)
        _path = '/'.join(_raw_path.split('/')[:_def.count('/')+1])
        if verbose:
            print 'RAW PATH', _raw_path
            print 'PATH    ', _path
        super(TTDirBase, self).__init__(_path, hint=hint, tmpl=_tmpl)


class TTRootBase(TTDirBase):
    """Base class for shot/asset root object."""

    step_type = None

    def find_steps(self, class_=None):
        """Find steps in this shot.

        Args:
            class_ (TTShotStepRoot): override step root class

        Returns:
            (TTShotStepRoot list): list of steps
        """
        _class = class_ or self.step_type
        _steps = []
        for _path in self.find(depth=1, type_='d'):
            try:
                _step = _class(_path)
            except ValueError:
                continue
            _steps.append(_step)

        return _steps


class TTStepRootBase(TTDirBase):
    """Base class for any shot/asset step root."""

    work_area_maya_hint = None
    work_area_maya_type = None

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path within step root
        """
        super(TTStepRootBase, self).__init__(path)
        self.name = self.step

    def get_work_area(self, dcc='maya'):
        """Get work area in this step for the given dcc.

        Args:
            dcc (str): dcc to get work area for

        Returns:
            (TTWorkAreaBase): work area
        """
        if dcc == 'maya':
            _tmpl = get_template(self.work_area_maya_hint)
            return self.work_area_maya_type(_tmpl.apply_fields(self.data))
        raise ValueError(dcc)


class TTWorkAreaBase(TTDirBase):
    """Base class for any work area tank template."""

    def get_metadata(self, verbose=0):
        """Read this work area's metadata yaml file.

        Args:
            verbose (int): print process data

        Returns:
            (dict): work area metadata
        """
        lprint("Reading metadata yaml", self.yaml, verbose=verbose)
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
        self.ver_fmt = self.path.replace(
            'v{:03d}'.format(self.version), 'v{:03d}')

    def find_latest(self, vers=None):
        """Find latest version of this work file stream.

        Args:
            vers (TTWorkFileBase list): override versions list

        Returns:
            (TTWorkFileBase): latest version
        """
        _vers = vers or self.find_vers()
        return _vers[-1]

    def find_next(self, vers=None):
        """Find next version.

        Args:
            vers (TTWorkFileBase list): override versions list

        Returns:
            (TTWorkFileBase): next version
        """
        _latest = self.find_latest(vers=vers)
        _data = copy.copy(_latest.data)
        _data['version'] = _latest.version + 1
        _path = get_template(_latest.hint).apply_fields(_data)
        return self.__class__(_path)

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

    def get_metadata(self, data=None, catch=True, verbose=1):
        """Get metadata for this work file.

        This can be expensive - it should read at work area level and
        then passed using the data arg.

        Args:
            data (dict): override data dict rather than read from disk
            catch (bool): no error on work file missing from metadata
            verbose (int): print process data
        """
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
            verbose=verbose)
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

    def get_work_area(self):
        """Get work area associated with this work file.

        Returns:
            (TTWorkAreaBase): work area
        """
        return self.work_area_type(self.path)

    def load(self):
        """Load this work file."""
        _engine = tank.platform.current_engine()
        _fileops = _engine.apps['psy-multi-fileops']
        _work_file = _fileops.get_workfile_from_path(self.path)
        _fileops.open_file(
            _work_file, open=True, force=True, change_context=True)

    def save(self, comment):
        """Save this version.

        Args:
            comment (str): comment for version
        """
        _fileops = tank.platform.current_engine().apps['psy-multi-fileops']
        _handler = _fileops._fileops_handler
        _mod = find_tank_mod('workspace', app='psy-multi-fileops')

        # Build tk objects
        if not self.exists():  # Version up

            # Get prev workfile
            _prev = self.find_vers()[-1]
            assert _prev.version == self.version - 1
            _tk_workspace = _mod.get_workspace_from_path(
                app=_fileops, path=_prev.path)
            _tk_workfile = _mod.WorkfileModel(
                workspace=_tk_workspace, template=_prev.tmpl,
                path=_prev.path)
            _tk_workfile = _tk_workfile.get_next_version()

            # Save
            _tk_workfile.save()

        elif self.path == host.cur_scene():  # Save over
            raise NotImplementedError
            # _metadata = {'comment': self.get_comment()}
            # print _handler.save_increment_file(metadata=_metadata)
            # _tk_workspace = _mod.get_workspace_from_path(
            #     app=_fileops, path=self.path)
            # _tk_workfile = _mod.WorkfileModel(
            #     workspace=_tk_workspace, template=self.tmpl,
            #     path=self.path)

        else:
            raise ValueError("Unhandled")

        # Save metadata
        _tk_workfile.metadata.comment = comment
        _tk_workfile.metadata.save()
        _fileops.user_settings.add_workfile_to_recent_settings(_tk_workfile)

    def set_comment(self, comment):
        """Set comment for this work file.

        Args:
            comment (str): comment to apply
        """
        _work_area = self.get_work_area()
        _metadata = copy.copy(_work_area.get_metadata(verbose=1))

        _updated = False
        for _idx, _task_data in enumerate(_metadata['workfiles']):
            if not _task_data['name'] == self.task:
                continue
            for _jdx, _ver_data in enumerate(_task_data['versions']):
                if not _ver_data['version'] == self.version:
                    continue
                print 'UPDATE {} -> {}'.format(_ver_data['comment'], comment)
                _updated = True
                _versions = _metadata['workfiles'][_idx]['versions']
                assert (
                    _versions[_jdx]['comment'] ==
                    _ver_data['comment'])
                _versions[_jdx]['comment'] = comment
                _work_area.set_metadata(_metadata)

        if not _updated:
            raise ValueError("Failed to update metadata "+self.path)


class TTOutputVerBase(TTDirBase):
    """Base class for any tank template version dir."""

    task = None
    version = None

    @property
    def vers_dir(self):
        """Stores directory containing versions."""
        return os.path.dirname(self.path)

    def find_latest(self):
        """Find latest version.

        Returns:
            (TTOutputVerBase): latest version
        """
        _vers = find(self.vers_dir, depth=1, type_='d', full_path=False)
        _data = copy.copy(self.data)
        _data['version'] = int(_vers[-1][1:])
        _path = self.tmpl.apply_fields(_data)
        return self.__class__(_path)

    def get_status(self):
        """Generate status for this version.

        Returns:
            (str): version status
        """
        _latest = self.find_latest()
        if self == _latest:
            return 'up to date'
        return 'needs update (latest:v{:03d})'.format(_latest.version)

    def is_latest(self):
        """Test whether this version is the latest.

        Returns:
            (bool): latest state
        """
        return self == self.find_latest()
