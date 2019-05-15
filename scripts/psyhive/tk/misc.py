"""General utilities."""

import tank

from psyhive.utils import store_result, get_single


@store_result
def get_project_data(project):
    """Get tank request data for the given project.

    Args:
        project (Project): project

    Returns:
        (dict): search data
    """
    _data = tank.platform.current_engine().shotgun.find(
        "Project", filters=[["name", "is", project.name]])
    _id = get_single(_data)['id']
    return {'type': 'Project', 'id': _id, 'name': project.name}


@store_result
def get_shot_data(shot):
    """Get tank request data for the given shot.

    Args:
        shot (Shot): shot

    Returns:
        (dict): search data
    """
    _data = tank.platform.current_engine().shotgun.find(
        'Shot', filters=[
            ["project", "is", [get_project_data(shot.project)]],
            ["code", "is", shot.name],
        ])
    _id = get_single(_data)['id']
    return {'type': 'Shot', 'id': _id, 'name': shot.name}
