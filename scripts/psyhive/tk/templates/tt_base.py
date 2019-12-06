"""Base classes for tank templates pipeline data."""

import copy
import pprint
import operator

import tank

from psyhive import pipe
from psyhive.utils import (
    get_single, Dir, abs_path, Path, lprint, apply_filter)

from psyhive.tk.templates.tt_misc import get_template
from psyhive.tk.misc import get_current_engine


class TTBase(Path):
    """Base class for any tank template object."""

    shot = None
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

    def map_to(self, class_=None, **kwargs):
        """Map this template's values to a different template.

        For example, this could be used to map a maya work file to
        a output file seq. If additional data is required, this can
        be passed in the kwargs.

        Args:
            class_ (TTBase): template type to map to

        Returns:
            (TTBase): new template instance
        """
        _class = class_ or type(self)
        _data = copy.copy(self.data)
        for _key, _val in kwargs.items():
            _data[_key] = _val
        _tmpl = get_template(_class.hint)
        try:
            _path = _tmpl.apply_fields(_data)
        except tank.TankError as _exc:
            _tags = '['+_exc.message.split('[')[-1]
            raise ValueError('Missing tags: '+_tags)
        return _class(_path)


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
        _tmpl = get_current_engine().tank.templates[_hint]
        _def = abs_path(_tmpl.definition, root=pipe.Project(path).path)
        _path = '/'.join(_raw_path.split('/')[:_def.count('/')+1])
        if verbose:
            print 'RAW PATH', _raw_path
            print 'PATH    ', _path
        super(TTDirBase, self).__init__(_path, hint=hint, tmpl=_tmpl)


class TTRootBase(TTDirBase):
    """Base class for shot/asset root object."""

    step_root_type = None

    def find_step_root(self, step, catch=False):
        """Find step root matching the given name.

        Args:
            step (str): step to search for
            catch (bool): no error on fail to find step root

        Returns:
            (TTStepRootBase): matching step root
        """
        return get_single([_root for _root in self.find_step_roots()
                           if _root.step == step], catch=catch)

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

    def find_output_name(self, output_name=None, task=None):
        """Find output name within this step root.

        Args:
            output_name (str): filter by output name
            task (str): filter by task

        Returns:
            (TTOutputNameBase): matching output name
        """
        _names = self.find_output_names(
            output_name=output_name, task=task, verbose=0)
        return get_single(_names, verbose=1)

    def find_output_names(self, output_name=None, output_type=None,
                          task=None, filter_=None, verbose=1):
        """Find output names within this step root.

        Args:
            output_name (str): filter by output name
            output_type (str): filter by output type
            task (str): filter by task
            filter_ (str): apply filter to paths
            verbose (int): print process data

        Returns:
            (TTOutputNameBase list): output names list
        """
        _names = self.read_output_names(verbose=verbose)
        if filter_:
            _names = apply_filter(
                _names, filter_, key=operator.attrgetter('path'))
        if output_name:
            _names = [_name for _name in _names
                      if _name.output_name == output_name]
        if output_type:
            _names = [_name for _name in _names
                      if _name.output_type == output_type]
        if task:
            _names = [_name for _name in _names if _name.task == task]
        return _names

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

    def read_output_names(self, filter_=None, verbose=1):
        """Find output names within this step root.

        Args:
            filter_ (str): apply path filter
            verbose (int): print process data

        Returns:
            (TTOutputNameBase list): output names list
        """
        lprint('SEARCHING FOR OUTPUT NAMES', self, verbose=verbose)
        _root = self.map_to(self.output_root_type)
        return _root.find(depth=2, type_='d', class_=self.output_name_type,
                          filter_=filter_)
