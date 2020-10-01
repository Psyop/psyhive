"""Tools for managing base/root tank template representations."""

import copy
import operator
import pprint
import tempfile

import tank

from psyhive import pipe, host
from psyhive.utils import (
    Path, abs_path, lprint, Dir, find, apply_filter, get_single,
    passes_filter, obj_read, obj_write, File)

from psyhive.tk2.tk_templates.tt_utils import get_area, get_dcc, get_template
from psyhive.tk2.tk_utils import get_current_engine


class TTBase(Path):
    """Base class for any tank template object."""

    asset = None
    sg_asset_type = None
    sequence = None
    shot = None
    step = None
    hint = None

    hint_fmt = None

    def __init__(
            self, path, hint, tmpl=None, data=None, verbose=0):
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
        self.tmpl = tmpl or get_current_engine().tank.templates[self.hint]

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

        self.area = get_area(_path)
        self.dcc = get_dcc(_path, allow_none=True)

    @property
    def cache_fmt(self):
        """Get generic cache format path.

        By default, data is cached to tmp dir.

        Returns:
            (str): cache format
        """
        _rel_path = File(Dir(pipe.cur_project().path).rel_path(self.path))
        return abs_path('{}/psyhive_cache/{}/{}_{{}}.{}'.format(
            tempfile.gettempdir(), _rel_path.dir, self.basename, self.extn))

    def cache_read(self, tag):
        """Read cached data from the given tag.

        Args:
            tag (str): data tag to read

        Returns:
            (any): cached data
        """
        _file = self.cache_fmt.format(tag)
        try:
            return obj_read(file_=_file)
        except OSError:
            return None

    def cache_write(self, tag, data):
        """Write data to the given cache.

        Args:
            tag (str): tag to store data to
            data (any): data to store
        """
        _file = self.cache_fmt.format(tag)
        obj_write(file_=_file, obj=data)

    def get_shot(self):
        """Get shot object for this path.

        Returns:
            (TTShot|None): shot (if any)
        """
        if not self.shot:
            return None
        return TTShot(self.path)

    def map_to(self, class_=None, hint=None, verbose=0, **kwargs):
        """Map this template's values to a different template.

        For example, this could be used to map a maya work file to
        a output file seq. If additional data is required, this can
        be passed in the kwargs.

        Args:
            class_ (TTBase): template type to map to
            hint (str): hint to map to
            verbose (int): print process data

        Returns:
            (TTBase): new template instance
        """
        _class = class_ or self.__class__
        lprint('CLASS', _class, class_, verbose=verbose)

        # Get hint
        _hint = hint
        if not _hint:
            _dcc = None
            if '{dcc}' in _class.hint_fmt:
                _dcc = kwargs.get('dcc', self.dcc)
                if not _dcc:  # Try to determine dcc from extn
                    _extn = kwargs.get('extension')
                    _dcc = {'mb': 'maya', 'ma': 'maya'}.get(_extn)
                if '{dcc}' in _class.hint_fmt and not _dcc:
                    raise ValueError('No value for dcc')
            _hint = _class.hint_fmt.format(area=self.area, dcc=_dcc)

        # Apply data to hint
        _data = copy.copy(self.data)
        for _key, _val in kwargs.items():
            _data[_key] = _val
        _tmpl = get_template(_hint)

        try:
            _path = _tmpl.apply_fields(_data)
        except tank.TankError as _exc:
            _tags = '['+_exc.message.split('[')[-1]
            raise ValueError('Missing tags: '+_tags)

        return _class(_path)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__.strip('_'), self.path)


class TTDirBase(Dir, TTBase):
    """Base class for any tank template directoy object."""

    def __init__(self, path, hint, verbose=0):
        """Constructor.

        Args:
            path (str): path to object
            hint (str): template name
            verbose (int): print process data
        """
        _raw_path = abs_path(path)
        _hint = hint or self.hint
        _tmpl = get_current_engine().tank.templates[_hint]
        _def = abs_path(_tmpl.definition, root=pipe.Project(path).path)
        _path = '/'.join(_raw_path.split('/')[:_def.count('/')+1])
        if verbose:
            print 'RAW PATH', _raw_path
            print 'PATH    ', _path
        super(TTDirBase, self).__init__(_path, hint=hint, tmpl=_tmpl)


class TTSequenceRoot(TTDirBase):
    """Represents a sequence root containing shot folders."""

    sequence = None
    hint_fmt = 'sequence_root'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to sequence root
        """
        super(TTSequenceRoot, self).__init__(path, hint=self.hint_fmt)

    def find_shots(self, filter_=None, class_=None):
        """Find shots in this sequence.

        Args:
            filter_ (str): filter by shot name
            class_ (TTRoot): override shot class

        Returns:
            (TTRoot list): list of shots
        """
        _shots = []
        for _shot in self._read_shots(class_=class_):
            if filter_ and not passes_filter(_shot.name, filter_):
                continue
            _shots.append(_shot)
        return _shots

    @property
    def name(self):
        """Get step type."""
        return self.sequence

    def _read_shots(self, class_=None):
        """Find shots in this sequence.

        Args:
            class_ (class): override shot class

        Returns:
            (TTRoot list): list of shots
        """
        _class = class_ or TTShot
        return self.find(depth=1, class_=_class)


class TTRoot(TTDirBase):
    """Represents a shot/asset root directory."""

    asset = None
    shot = None
    hint_fmt = '{area}_root'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to root dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)
        super(TTRoot, self).__init__(path, hint=_hint)
        if self.shot:
            self.name = self.shot
        else:
            self.name = self.asset

    def create_workspaces(self, force=False):
        """Create workspaces on disk for this asset/shot.

        Args:
            force (bool): create workspaces without confirmation
        """
        from psyhive import tk2
        tk2.create_workspaces(self, force=force)

    def find_step_root(self, step, catch=False):
        """Find step root matching the given name.

        Args:
            step (str): step to search for
            catch (bool): no error on no step found

        Returns:
            (TTStepRoot): matching step root
        """
        return get_single([_root for _root in self.find_step_roots()
                           if _root.step == step], catch=catch)

    def find_step_roots(self, class_=None, filter_=None):
        """Find steps in this shot.

        Args:
            class_ (TTStepRoot): override step root class
            filter_ (str): filter the list of steps

        Returns:
            (TTStepRoot list): list of steps
        """
        _step_root = self._read_step_roots(class_=class_)
        return apply_filter(
            _step_root, filter_, key=operator.attrgetter('path'))

    def get_sg_data(self):
        """Get shotgun data for this root.

        Returns:
            (dict): sg data
        """
        from psyhive import tk2
        if self.shot:
            return tk2.get_shot_sg_data(self)
        if self.asset:
            return tk2.get_asset_sg_data(self)
        raise RuntimeError

    def _read_step_roots(self, class_=None):
        """Find steps in this shot.

        Args:
            class_ (TTStepRoot): override step root class

        Returns:
            (TTStepRoot list): list of steps
        """
        _class = class_ or TTStepRoot
        return self.find(depth=1, type_='d', class_=_class)


class TTAsset(TTRoot):
    """Represents an asset folder."""


class TTShot(TTRoot):
    """Represents a shot folder."""

    @property
    def idx_s(self):
        """Get shot index string.

        Returns:
            (str): index str (eg. 0010)
        """
        _idx_s = ''
        for _chr in reversed(self.name):
            if not _chr.isdigit():
                break
            _idx_s = _chr+_idx_s
        return _idx_s

    @property
    def idx(self):
        """Get shot index.

        Returns:
            (int): shot index (eg. 10)
        """
        return int(self.idx_s)

    def get_frame_range(self, use_cut=True):
        """Read shot frame range from shotgun.

        This uses head in/tail out data values.

        Args:
            use_cut (bool): use cut in/out data

        Returns:
            (tuple): start/end frames
        """
        from psyhive import tk2
        _shotgun = tank.platform.current_engine().shotgun
        _fields = _get_rng_fields(use_cut)
        _sg_data = _shotgun.find_one(
            "Shot", filters=[
                ["project", "is", [tk2.get_project_sg_data(self.project)]],
                ["code", "is", self.name],
            ],
            fields=_fields)
        if not _sg_data:
            return (None, None)
        return tuple([_sg_data[_field] for _field in _fields])

    def set_frame_range(self, rng, use_cut=True):
        """Set frame range in shotgun.

        Args:
            rng (int tuple): start/end frames
            use_cut (bool): set cut in/out fields
        """
        _start, _end = rng
        _fields = _get_rng_fields(use_cut)
        _data = {_fields[0]: _start, _fields[1]: _end}
        _sg = tank.platform.current_engine().shotgun
        _sg.update(
            entity_type='Shot',
            entity_id=self.get_sg_data()['id'],
            data=_data)


def _get_rng_fields(use_cut):
    """Get shotgun frame range fields.

    Args:
        use_cut (bool): use cut in/out

    Returns:
        (list): range fields
    """
    if not use_cut:
        return ["sg_head_in", "sg_tail_out"]
    return ["sg_cut_in", "sg_cut_out"]


class TTStepRoot(TTDirBase):
    """Represents a step root dir containing step folders."""

    asset = None
    sequence = None
    shot = None
    step = None
    sg_asset_type = None

    hint_fmt = '{area}_step_root'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to step root
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)
        super(TTStepRoot, self).__init__(path, hint=_hint)
        self.name = self.step

    def find_output_types(self, output_type=None):
        """Find output types in this step root.

        Args:
            output_type (str): filter by output_type name

        Returns:
            (TTOutputType list): output types
        """
        _types = self._read_output_types()
        if output_type is not None:
            _types = [_type for _type in _types
                      if _type.output_type == output_type]
        return _types

    def find_output_name(self, output_name=None, task=None):
        """Find output name within this step root.

        Args:
            output_name (str): filter by output name
            task (str): filter by task

        Returns:
            (TTOutputName): matching output name
        """
        _names = self.find_output_names(
            output_name=output_name, task=task)
        return get_single(_names, verbose=1)

    def find_output_names(self, output_name=None, output_type=None,
                          task=None, filter_=None, verbose=0):
        """Find output names within this step root.

        Args:
            output_name (str): filter by output name
            output_type (str): filter by output type
            task (str): filter by task
            filter_ (str): apply filter to paths
            verbose (int): print process data

        Returns:
            (TTOutputName list): output names list
        """
        _names = []
        for _type in self.find_output_types(output_type=output_type):
            lprint('TESTING TYPE', _type, verbose=verbose)
            _names += _type.find_names(
                output_name=output_name, filter_=filter_, task=task,
                verbose=verbose)
        return _names

    def find_output_versions(
            self, filter_=None, task=None, version=None,
            output_type=None, output_name=None, verbose=0):
        """Find outputs within this step root.

        Args:
            filter_ (str): file path filter
            task (str): filter by task
            version (str): filter by version (eg. v003 or latest)
            output_type (str): filter by version type
            output_name (str): filter by output name
            verbose (int): print process data

        Returns:
            (TTOutput list): list of outputs
        """
        _vers = []
        for _name in self.find_output_names(
                task=task, output_type=output_type,
                output_name=output_name):
            lprint('TESTING NAME', _name, verbose=verbose)
            _vers += _name.find_versions(filter_=filter_, version=version)
        return _vers

    def find_outputs(self, filter_=None, task=None, version=None,
                     output_type=None, output_name=None, verbose=0):
        """Find outputs within this step root.

        Args:
            filter_ (str): file path filter
            task (str): filter by task
            version (str): filter by version (eg. v003 or latest)
            output_type (str): filter by version type
            output_name (str): filter by output name
            verbose (int): print process data

        Returns:
            (TTOutput list): list of outputs
        """
        _outs = []
        for _ver in self.find_output_versions(
                task=task, output_type=output_type,
                output_name=output_name, version=version):
            lprint('TESTING VER', _ver, verbose=verbose)
            _outs += _ver.find_outputs(filter_=filter_)
        return _outs

    def find_output_file(
            self, format_=None, extn=None, version=None, task=None,
            catch=False, verbose=0):
        """Find a specific output file in this step root.

        Args:
            format_ (str): filter by format (eg. maya)
            extn (str): filter by extension (eg. mb)
            version (str): filter by version (eg. v003 or latest)
            task (str): filter by task
            catch (bool): no error on fail
            verbose (int): print process data

        Returns:
            (TTOutputFileBase): matching output file
        """
        _files = self.find_output_files(
            format_=format_, extn=extn, version=version, task=task)
        return get_single(_files, catch=catch, verbose=verbose)

    def find_output_files(
            self, format_=None, extn=None, version=None, task=None):
        """Find output files in this step root.

        Args:
            format_ (str): filter by format (eg. maya)
            extn (str): filter by extension (eg. mb)
            version (str): filter by version (eg. v003 or latest)
            task (str): filter by task

        Returns:
            (TTOutputFileBase list): matching output files
        """
        _files = []
        for _out in self.find_outputs(version=version, task=task):
            _files += _out.find_files(
                format_=format_, extn=extn)
        return _files

    def find_renders(self):
        """Find renders in this step root.

        Returns:
            (TTOutputName list): output names list
        """
        return [_name for _name in self.find_output_names()
                if _name.output_type == 'render']

    def find_work(self, dcc=None, class_=None, task=None):
        """Find work files inside this step root.

        Args:
            dcc (str): dcc to find work for
            class_ (class): override work class
            task (str): filter by task

        Returns:
            (TTWork list): list of work files
        """
        return self.get_work_area(dcc=dcc).find_work(
            class_=class_, task=task)

    def find_tasks(self):
        """Find tasks in this step.

        Returns:
            (str list): tasks
        """
        return sorted(set([_work.task for _work in self.find_work()]))

    def get_work_area(self, dcc):
        """Get work area in this step for the given dcc.

        Args:
            dcc (str): dcc to get work area for

        Returns:
            (TTWorkArea): work area
        """
        from psyhive.tk2.tk_templates.tt_work import TTWorkArea
        _dcc = dcc or host.NAME
        _hint = '{}_work_area_{}'.format(self.area, _dcc)
        _tmpl = get_template(_hint)
        _path = _tmpl.apply_fields(self.data)
        return TTWorkArea(_path)

    def _read_output_types(self, class_=None):
        """Read output types in this step root from disk.

        Args:
            class_ (class): override output type class

        Returns:
            (TTOutputType list): output type list
        """
        from psyhive.tk2.tk_templates.tt_output import TTOutputType
        _hint = '{}_output_root'.format(self.area)
        _tmpl = get_template(_hint)
        _root = _tmpl.apply_fields(self.data)
        return find(_root, depth=1, class_=class_ or TTOutputType)
