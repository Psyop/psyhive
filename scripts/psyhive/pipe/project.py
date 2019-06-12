"""Tools for managing projects."""

import operator
import os

from psyhive.utils import (
    find, store_result, Dir, get_single, lprint, passes_filter,
    apply_filter)

PROJECTS_ROOT = 'P:/projects'


class Project(Dir):
    """Represents a project on disk."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path within a project

        Raises:
            (ValueError): if path was not in projects root
        """
        _tokens = Dir(PROJECTS_ROOT).rel_path(path).split('/')
        _path = '/'.join([PROJECTS_ROOT, _tokens[0]])
        super(Project, self).__init__(_path)
        self.name = _tokens[0]
        if self.name.startswith('~'):
            raise ValueError
        self.seqs_path = '/'.join([self.path, 'sequences'])

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

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.name)


def cur_project():
    """Get current project.

    Returns:
        (Project): current project
    """
    return Project(os.environ['PSYOP_PROJECT_PATH'])


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


def find_project(name):
    """Find a project matching the given name.

    Args:
        name (str): project name to search for

    Returns:
        (Project): matching project
    """
    _projs = find_projects()
    _ematch = get_single(
        [_project for _project in _projs if _project.name == name],
        catch=True)
    if _ematch:
        return _ematch
    _fmatch = get_single(
        apply_filter(_projs, name, key=operator.attrgetter('name')))
    return _fmatch


def get_project(name):
    """Get project matching give name.

    Args:
        name (str): project name

    Returns:
        (Project): project
    """
    return Project(PROJECTS_ROOT+'/'+name)
