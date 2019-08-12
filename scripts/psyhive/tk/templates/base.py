"""Tools for accessing tank pipeline data."""

import copy
import os
import pprint
import tempfile
import shutil

import tank

from tank.platform import current_engine

from psyhive import pipe, qt
from psyhive.utils import (
    get_single, Dir, File, abs_path, find, Path, dprint,
    lprint, read_yaml, write_yaml, diff, Seq)

from psyhive.tk.templates.misc import get_template
from psyhive.tk.misc import find_tank_mod, find_tank_app


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

    def map_to(self, class_, **kwargs):
        """Map this template's values to a different template.

        For example, this could be used to map a maya work file to
        a output file seq. If additional data is required, this can
        be passed in the kwargs.

        Args:
            class_ (TTBase): template type to map to

        Returns:
            (TTBase): new template instance
        """
        _data = copy.copy(self.data)
        for _key, _val in kwargs.items():
            _data[_key] = _val
        _tmpl = get_template(class_.hint)
        try:
            _path = _tmpl.apply_fields(_data)
        except tank.TankError as _exc:
            _tags = '['+_exc.message.split('[')[-1]
            raise ValueError('Missing tags: '+_tags)
        return class_(_path)


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

    step_root_type = None

    def find_step_roots(self, class_=None, filter_=None):
        """Find steps in this shot.

        Args:
            class_ (TTShotStepRoot): override step root class
            filter_ (str): filter the list of steps

        Returns:
            (TTShotStepRoot list): list of steps
        """
        _class = class_ or self.step_root_type
        _steps = []
        for _path in self.find(depth=1, type_='d', filter_=filter_):
            try:
                _step = _class(_path)
            except ValueError:
                continue
            _steps.append(_step)

        return _steps


class TTStepRootBase(TTDirBase):
    """Base class for any shot/asset step root."""

    asset = None
    maya_work_type = None
    output_name_type = None
    output_root_type = None
    sequence = None
    sg_asset_type = None
    work_area_maya_hint = None
    work_area_maya_type = None

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path within step root
        """
        super(TTStepRootBase, self).__init__(path)
        self.name = self.step

    def find_output_names(self, verbose=1):
        """Find output names within this step root.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutputNameBase list): output names list
        """
        lprint('SEARCHING FOR OUTPUT NAMES', self, verbose=verbose)
        _root = self.map_to(self.output_root_type)
        return _root.find(depth=2, type_='d', class_=self.output_name_type)

    def find_renders(self):
        """Find renders in this step root.

        Returns:
            (TTOutputNameBase list): output names list
        """
        return [_name for _name in self.find_output_names()
                if _name.output_type == 'render']

    def find_work_files(self):
        """Find work files inside this step root.

        Args:
            cacheable (bool):

        Returns:
            (TTWorkFileBase list): list of work files
        """
        _works = []
        _work_type = self.maya_work_type
        for _file in self.get_work_area().find(depth=2, type_='f'):
            try:
                _work = _work_type(_file)
            except ValueError:
                continue
            _works.append(_work)
        return _works

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

        assert self.exists()

        _tk_workspace = _mod.get_workspace_from_path(
            app=_fileops, path=self.path)
        _tk_workfile = _mod.WorkfileModel(
            workspace=_tk_workspace, template=self.tmpl,
            path=self.path)
        _fileops.user_settings.add_workfile_to_recent_settings(_tk_workfile)

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

    def find_output_names(self, verbose=0):
        """Find output names for this work file.

        Args:
            verbose (int): print process data

        Returns:
            (list): list of output names
        """
        _root_tmpl = get_template(self.output_root_type.hint)
        _root = self.output_root_type(_root_tmpl.apply_fields(self.data))
        lprint('ROOT', _root, verbose=verbose)
        _names = []
        for _dir in _root.find(depth=2, type_='d'):
            try:
                _name = self.output_name_type(_dir)
            except ValueError:
                continue
            if not _name.task == self.task:
                continue
            lprint(' - ADDED NAME', _name, verbose=verbose)
            _names.append(_name)
        return _names

    def find_outputs(self, verbose=1):
        """Find outputs from this work file.

        Args:
            verbose (int): print process data

        Returns:
            (TTAssetOutputFile list): list of outputs
        """
        _ver_tmpl = get_template(self.output_version_type.hint)

        # Find vers that exist in each name
        lprint('SEARCHING FOR VERSIONS', verbose=verbose)
        _vers = []
        for _name in self.find_output_names():
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
            _outputs += _ver.find_outputs()

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

        qt.get_application().processEvents()  # outputpaths is deferred load
        _outputpaths = tk.find_tank_app('outputpaths')
        _outputpaths.update_output_paths()

    def save(self, comment):
        """Save this version.

        Args:
            comment (str): comment for version
        """
        _fileops = find_tank_app('psy-multi-fileops')
        _mod = find_tank_mod('workspace', app='psy-multi-fileops')
        _prev = self.find_latest()

        assert not self.exists()  # Must be version up

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

        # Save
        _tk_workfile.save()

        # Save metadata
        self.set_comment(comment)
        self.add_to_recent()

    def set_comment(self, comment):
        """Set comment for this version.

        Args:
            comment (str): comment to apply
        """
        _fileops = find_tank_app('psy-multi-fileops')
        _mod = find_tank_mod('workspace', app='psy-multi-fileops')

        assert self.exists()

        _tk_workspace = _mod.get_workspace_from_path(
            app=_fileops, path=self.path)
        _tk_workfile = _mod.WorkfileModel(
            workspace=_tk_workspace, template=self.tmpl,
            path=self.path)
        _tk_workfile.metadata.comment = comment
        _tk_workfile.metadata.save()


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


class TTOutputVersionBase(TTDirBase):
    """Base class for any tank template version dir."""

    maya_work_type = None
    output_file_seq_type = None
    output_file_type = None
    task = None
    version = None

    def find_latest(self):
        """Find latest version.

        Returns:
            (TTOutputVersionBase): latest version
        """
        _vers = find(self.vers_dir, depth=1, type_='d', full_path=False)
        _data = copy.copy(self.data)
        _data['version'] = int(_vers[-1][1:])
        _path = self.tmpl.apply_fields(_data)
        return self.__class__(_path)

    def find_outputs(self, thumbs=False, verbose=0):
        """Find outputs in this version.

        Args:
            thumbs (bool): include thumbs
            verbose (int): print process data

        Returns:
            (TTOutputFileBase|TTOutputFileSeqBase list): outputs
        """
        lprint('SEARCHING FOR OUTPUTS', verbose=verbose)

        _files = self.find(type_='f', depth=3)
        lprint(' - FOUND {:d} FILES'.format(len(_files)), verbose=verbose)

        # Map files to outputs
        _outputs = []
        _seqs = {}
        for _file in _files:

            # Ignore files already matched in seq
            _already_matched = False
            for _seq in _seqs:
                if _seq.contains(_file):
                    _already_matched = True
                    _frame = _seq.get_frame(_file)
                    _seqs[_seq].add(_frame)
                    break
            if _already_matched:
                continue

            _output = None
            lprint(' - TESTING', _file, verbose=verbose > 1)

            # Match seq
            try:
                _output = self.output_file_seq_type(_file)
            except ValueError:
                lprint('   - NOT OUTPUT FILE SEQ', _file,
                       verbose=verbose > 1)
            else:
                _frame = _output.get_frame(_file)
                _seqs[_output] = set([_frame])

            # Match file
            if not _output:
                try:
                    _output = self.output_file_type(_file)
                except ValueError:
                    lprint('   - NOT OUTPUT FILE', _file,
                           verbose=verbose > 1)

            if _output:
                lprint(' - ADDED OUTPUT', _output, verbose=verbose)
                _outputs.append(_output)

        # Apply frames cache
        for _seq, _frames in _seqs.items():
            _seq.set_frames(sorted(_frames))

        if not thumbs:
            for _output in copy.copy(_outputs):
                if _output.data.get('channel') == '.thumbs':
                    _outputs.remove(_output)

        return _outputs

    def find_work_file(self, verbose=1):
        """Find work file this output was generated from.

        Args:
            verbose (int): print process data

        Returns:
            (TTWorkFileBase|None): associated work file (if any)
        """
        for _extn in ['ma', 'mb']:
            _work = self.map_to(self.maya_work_type, extension=_extn)
            lprint(' - CHECKING WORK', _work, verbose=verbose)
            if _work.exists():
                return _work
        return None

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

    @property
    def vers_dir(self):
        """Stores directory containing versions."""
        return os.path.dirname(self.path)


class TTOutputFileBase(TTBase, File):
    """Base class for any output file tank template."""

    output_file_type = None
    output_name = None
    output_type = None
    output_version_type = None

    def find_latest(self):
        """Get latest version asset stream.

        Returns:
            (TTAssetOutputFile): latest asset output file
        """
        _ver = self.output_version_type(self.path)
        _latest = _ver.find_latest()
        _data = copy.copy(self.data)
        _data['version'] = _latest.version
        return self.output_file_type(self.tmpl.apply_fields(_data))

    def is_latest(self):
        """Check if this is the latest version.

        Returns:
            (bool): latest status
        """
        return self.find_latest() == self


class TTOutputFileSeqBase(TTBase, Seq):
    """Represents a shout output file seq tank template path."""

    output_version_type = None
    exists = Seq.exists

    def __init__(self, path, verbose=0):
        """Constructor.

        Args:
            path (str): file seq path
            verbose (int): print process data
        """
        _tmpl = get_template(self.hint)
        try:
            _data = _tmpl.get_fields(path)
        except tank.TankError as _exc:
            lprint('TANK ERROR', _exc.message, verbose=verbose)
            raise ValueError("Tank rejected path "+path)
        _data["SEQ"] = "%04d"
        _path = abs_path(_tmpl.apply_fields(_data))
        super(TTOutputFileSeqBase, self).__init__(
            path=_path, data=_data, tmpl=_tmpl)
        Seq.__init__(self, _path)

    def find_work_file(self):
        """Find work file corresponding to this seq.

        Returns:
            (TTWorkFileBase): work file
        """
        _base = self.output_version_type()(self.path)
        return _base.find_work_file()
