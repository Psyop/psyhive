"""Tools for managing base/root tank template representations."""

import copy
import operator
import pprint

import tank

from psyhive import pipe
from psyhive.utils import (
    Path, abs_path, lprint, Dir, find, apply_filter, get_single,
    passes_filter)

from psyhive.tk2.tk_templates.tt_utils import get_area, get_dcc, get_template
from psyhive.tk2.tk_utils import get_current_engine


class TTBase(Path):
    """Base class for any tank template object."""

    shot = None
    step = None
    hint = None

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

    def map_to(self, hint=None, class_=None, **kwargs):
        """Map this template's values to a different template.

        For example, this could be used to map a maya work file to
        a output file seq. If additional data is required, this can
        be passed in the kwargs.

        Args:
            hint (str): hint to map to
            class_ (TTBase): template type to map to

        Returns:
            (TTBase): new template instance
        """
        _hint = hint or self.hint
        _class = class_ or self.__class__
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

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to sequence root
        """
        super(TTSequenceRoot, self).__init__(path, hint='sequence_root')

    def find_shots(self, filter_=None, class_=None):
        """Find shots in this sequence.

        Args:
            filter_ (str): filter by shot name
            class_ (TTRoot): override shot class

        Returns:
            (TTRoot list): list of shots
        """
        _shots = []
        _class = class_ or TTRoot
        for _shot in self._read_shots():
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
        _class = class_ or TTRoot
        return self.find(depth=1, class_=_class)


class TTRoot(TTDirBase):
    """Represents a shot/asset root directory."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to root dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = '{}_root'.format(_area)
        super(TTRoot, self).__init__(path, hint=_hint)

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

    def _read_step_roots(self, class_=None):
        """Find steps in this shot.

        Args:
            class_ (TTStepRoot): override step root class

        Returns:
            (TTStepRoot list): list of steps
        """
        _class = class_ or TTStepRoot
        return self.find(depth=1, type_='d', class_=_class)


class TTStepRoot(TTDirBase):
    """Represents a step root dir containing step folders."""

    asset = None
    sequence = None
    shot = None
    step = None
    sg_asset_type = None

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to step root
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = '{}_step_root'.format(_area)
        super(TTStepRoot, self).__init__(path, hint=_hint)

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
                          task=None, filter_=None):
        """Find output names within this step root.

        Args:
            output_name (str): filter by output name
            output_type (str): filter by output type
            task (str): filter by task
            filter_ (str): apply filter to paths

        Returns:
            (TTOutputName list): output names list
        """
        _names = []
        for _type in self.find_output_types(output_type=output_type):
            _names += _type.find_names(
                output_name=output_name, filter_=filter_, task=task)
        return _names

    def find_outputs(self, filter_=None, task=None, version=None,
                     output_type=None):
        """Find outputs within this step root.

        Args:
            filter_ (str): file path filter
            task (str): filter by task
            version (str): filter by version
            output_type (str): filter by version type

        Returns:
            (TTOutput list): list of outputs
        """
        _outs = []
        for _name in self.find_output_names(
                task=task, output_type=output_type):
            for _ver in _name.find_versions(version=version):
                _outs += _ver.find_outputs(filter_=filter_)
        return _outs

    def find_renders(self):
        """Find renders in this step root.

        Returns:
            (TTOutputName list): output names list
        """
        return [_name for _name in self.find_output_names()
                if _name.output_type == 'render']

    def find_work(self, dcc=None):
        """Find work files inside this step root.

        Args:
            dcc (str): dcc to find work for

        Returns:
            (TTWork list): list of work files
        """
        return self.get_work_area(dcc=dcc).find_work()

    def get_work_area(self, dcc):
        """Get work area in this step for the given dcc.

        Args:
            dcc (str): dcc to get work area for

        Returns:
            (TTWorkArea): work area
        """
        from psyhive.tk2.tk_templates.tt_work import TTWorkArea
        _hint = '{}_work_area_{}'.format(self.area, dcc)
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
