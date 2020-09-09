"""Tools for managing shotgun queries."""

import collections
import pprint
import tank

from psyhive import pipe, qt
from psyhive.utils import store_result, get_single, get_plural


def get_sg_data(type_, fields=None, limit=10, verbose=0, **kwargs):
    """Search shotgun for data.

    Args:
        type_ (str): field type (eg. PublishedItem/Shot)
        fields (str list): fields to return (otherwise all are returned)
        limit (int): limit the number of items returned
        verbose (int): print process data

    Returns:
        (dict): shotgun data
    """
    _sg = tank.platform.current_engine().shotgun
    _fields = fields or _sg.schema_field_read(type_).keys()

    _filters = [(_key, 'is', _val) for _key, _val in kwargs.items()]
    _filters.append(['project', 'is', get_project_sg_data()])
    if verbose:
        print 'FILTERS:'
        pprint.pprint(_filters)

    _data = _sg.find(type_, filters=_filters, fields=_fields, limit=limit)
    return _data


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
def get_asset_sg_data(asset):
    """Get shotgun data for the given asset.

    Args:
        asset (TTRoot): asset to retrieve data for

    Returns:
        (dict): asset shotgun data
    """
    _data = get_single(tank.platform.current_engine().shotgun.find(
        'Asset', filters=[
            ["project", "is", [get_project_sg_data(asset.project)]],
            ["code", "is", asset.asset],
        ]))
    return _data


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
        "Project", filters=[["sg_code", "is", _project.name]])
    _id = get_single(_data)['id']
    return {'type': 'Project', 'id': _id, 'name': _project.name}


def get_root_sg_data(root):
    """Get shotgun data for the given tank template root object.

    Args:
        root (TTRoot): root object to read

    Returns:
        (dict): shotgun data
    """
    if root.shot:
        return get_shot_sg_data(root)
    elif root.asset:
        return get_asset_sg_data(root)
    raise ValueError(root)


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
    return {'type': 'Shot', 'id': _id, 'name': _get_shot_sg_name(shot.name)}


def create_workspaces(root):
    """Create workspaces within the given root asset/shot.

    This creates paths on disk for all of the steps which are attached
    to the root in shotgun.

    Args:
        root (TTRoot): asset/shot to create workspaces for
    """
    _proj = pipe.Project(root.path)
    _tk = tank.Sgtk(_proj.path)
    _ctx = _tk.context_from_path(_proj.path)

    # Set filter
    _filters = [
        ['project', 'is', _ctx.project],
        ['step', 'is_not', None],
        ['entity', 'is', get_shot_sg_data(root)],
    ]

    # Find tasks
    _sg = tank.platform.current_engine().shotgun
    _all_tasks = _sg.find(
        'Task', _filters, fields=['project', 'entity', 'step'])
    _key = lambda t: (t['project']['id'], t['entity']['id'], t['step']['id'])
    _all_tasks.sort(key=_key)
    _grouped_by_entity = collections.defaultdict(list)
    for _task in _all_tasks:
        _grouped_by_entity[(
            _task['entity']['type'], _task['entity']['id'],
            _task['entity']['name'])].append(_task)

    # Find tasks which need creating
    _to_create = []
    for (_entity_type, _entity_id, _entity_name), _tasks in sorted(
            _grouped_by_entity.items()):
        if _entity_type not in ('Asset', 'Shot', 'Sequence'):
            continue
        print _entity_name
        _entity_id_list = [_task['id'] for _task in _tasks]
        print 'CREATE', _entity_type, _entity_id, _entity_name, _entity_id_list
        _to_create.append((
            _entity_type, _entity_id, _entity_name, _entity_id_list))

    # Execute creation
    qt.ok_cancel('Create {:d} workspace{}?'.format(
        len(_to_create), get_plural(_to_create)))
    _done = list()
    for _entity_type, _entity_id, _entity_name, _entity_id_list in _to_create:
        _key = (_entity_type, _entity_id)
        if _key in _done:
            continue
        _tk.create_filesystem_structure('Task', _entity_id_list)
        print '...created workspace for %s/%s/%s\n' % (
            _ctx.project['name'], _entity_type, _entity_name)
        _done.append(_key)
