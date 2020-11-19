"""Tools for managing projects."""

import operator
import os

from psyhive.utils import (
    find, store_result, Dir, get_single, lprint, passes_filter,
    apply_filter, read_yaml, File, abs_path, Cacheable, get_cfg)

PROJECTS_ROOT = abs_path(
    os.environ.get('PSYOP_PROJECTS_ROOT', 'P:/projects'))
_PSYLAUNCH_CFG_FMT = r'{}\code\primary\config\psylaunch\settings.yml'


class Project(Dir, Cacheable):
    """Represents a project on disk."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path within a project

        Raises:
            (ValueError): if path was not in projects root
        """
        try:
            _tokens = Dir(PROJECTS_ROOT).rel_path(path).split('/')
        except ValueError:
            raise ValueError('Not in projects root '+path)
        _path = '/'.join([PROJECTS_ROOT, _tokens[0]])

        super(Project, self).__init__(_path)

        self.name = _tokens[0]
        if self.name.startswith('~'):
            raise ValueError

        self.seqs_path = '/'.join([self.path, 'sequences'])
        self.maya_scripts_path = '{}/code/primary/addons/maya/scripts'.format(
            os.environ.get('PSYOP_PROJECT_PATH'))
        self.psylaunch_cfg = abs_path(_PSYLAUNCH_CFG_FMT.format(self.path))
        self.cache_fmt = '{}/production/psyhive/cache/{{}}.pkl'.format(
            self.path)

    @property
    def code(self):
        """Get the project code.

        Returns:
            (int): code as integer
        """
        return int(self.name.split('_')[-1].strip('PVBIFM'))

    def find_shot(self, name):
        """Find shot matching the given name.

        Args:
            name (str): name to match

        Returns:
            (Shot): matching shot
        """
        _shots = self.find_shots()
        return get_single([_shot for _shot in _shots if _shot.name == name])

    def find_shots(self, filter_=None, verbose=0):
        """Find shots within this project.

        Args:
            filter_ (str): filter shot names
            verbose (int): print process data

        Returns:
            (Shot list): shots
        """
        from psyhive import pipe
        _shots = []
        lprint('SEARCHING', self.seqs_path, verbose=verbose)
        for _path in find(self.seqs_path, depth=2, type_='d'):
            try:
                _shot = pipe.Shot(_path)
            except ValueError:
                lprint(' - REJECTED', _path, verbose=verbose)
                continue
            if filter_ and not passes_filter(_shot.name, filter_):
                continue
            _shots.append(_shot)

        return _shots

    def get_cfg(self):
        """Get config for this project.

        Returns:
            (dict): project config
        """
        return get_cfg(namespace='psyhive', level='project', project=self)

    def read_psylaunch_cfg(self, edit=False, verbose=0):
        """Read psylaunch config data for this project.

        Args:
            edit (bool): open file in editor
            verbose (int): print process data

        Returns:
            (dict): psylaunch config data
        """
        _yaml = abs_path(_PSYLAUNCH_CFG_FMT.format(self.path))
        lprint('PSYLAUNCH YAML', _yaml, verbose=verbose)
        if edit:
            File(_yaml).edit()
        return read_yaml(_yaml)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.name)


def cur_project():
    """Get current project.

    Returns:
        (Project): current project
    """
    _name = os.environ.get('PSYOP_PROJECT_PATH')
    if not _name:
        return None
    return Project(_name)


@store_result
def find_projects(filter_=None):
    """Find projects on disk.

    Args:
        filter_ (str): filter projects by name

    Returns:
        (Project list): projects
    """
    _projects = []
    for _path in find(PROJECTS_ROOT, depth=1, type_='d'):
        try:
            _project = Project(_path)
        except ValueError:
            continue
        if not passes_filter(_project.name, filter_):
            continue
        _projects.append(_project)

    return _projects


def find_project(name, catch=False, verbose=0):
    """Find a project matching the given name.

    Args:
        name (str): project name to search for
        catch (bool): no error of project not found
        verbose (int): print process data

    Returns:
        (Project): matching project
    """
    _projs = find_projects()
    _ematch = get_single(
        [_project for _project in _projs if _project.name == name],
        catch=True, verbose=verbose)
    if _ematch:
        return _ematch
    _fmatch = get_single(
        apply_filter(_projs, name, key=operator.attrgetter('name')),
        verbose=verbose+1, catch=catch)
    return _fmatch


def get_project(name):
    """Get project matching give name.

    Args:
        name (str): project name

    Returns:
        (Project): project
    """
    return Project(PROJECTS_ROOT+'/'+name)
