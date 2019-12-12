"""Tools for managing shotgun queries."""

import tank

from psyhive import pipe
from psyhive.utils import store_result, get_single


@store_result
def _get_shot_sg_name(name):
    """Get shotgun name for a shot based on its disk name.

    The shotgun name will have an capitalised letter replaced with an
    underscore and the lower case letter

        eg. cid00_aid000 -> cir00Aid000

    Args:
        name (str): disk name

    Returns:
        (str): shotgun name
    """
    _sg_name = ''
    for _chr in name:
        if _chr.isupper():
            _sg_name += '_'
        _sg_name += _chr.lower()
    return _sg_name


@store_result
def get_project_sg_data(project=None):
    """Get tank request data for the given project.

    Args:
        project (Project): project

    Returns:
        (dict): search data
    """
    _project = project or pipe.cur_project()
    _data = tank.platform.current_engine().shotgun.find(
        "Project", filters=[["name", "is", _project.name]])
    _id = get_single(_data)['id']
    return {'type': 'Project', 'id': _id, 'name': _project.name}


@store_result
def get_shot_sg_data(shot):
    """Get tank request data for the given shot.

    Args:
        shot (Shot): shot

    Returns:
        (dict): search data
    """
    _sg_name = _get_shot_sg_name(shot.name)
    _data = tank.platform.current_engine().shotgun.find(
        'Shot', filters=[
            ["project", "is", [get_project_sg_data(shot.project)]],
            ["code", "is", _sg_name],
        ])
    if not _data:
        raise RuntimeError('Shot missing from shotgun {}'.format(shot.name))
    _id = get_single(_data)['id']
    return {'type': 'Shot', 'id': _id, 'name': shot.name}
