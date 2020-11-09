"""Tools for managing config files."""

import os

from .path import abs_path, File
from .misc import lprint


def _get_cfg_yaml(level, namespace, project=None, verbose=0):
    """Get path to config yaml file.

    Args:
        level (str): config level (eg. code/project)
        namespace (str): namespace name to read from
        project (Project): project to read config from (if level is project)
        verbose (int): print process data

    Returns:
        (File): config yaml
    """
    if level == 'code':
        _yml = abs_path(
            '../../../cfg/{}.yml'.format(namespace),
            root=os.path.dirname(__file__))
    elif level == 'project':
        from psyhive import pipe
        _proj = project or pipe.cur_project()
        _yml = '{}/production/psyhive/cfg/{}.yml'.format(
            _proj.path, namespace)
    else:
        raise ValueError(level)
    lprint('YAML', _yml, verbose=verbose)
    return File(_yml)


def get_cfg(namespace, level='code', catch=True, project=None, verbose=0):
    """Read config from the given namespace.

    Args:
        namespace (str): namespace name to read from
        level (str): config level (eg. code/project)
        catch (bool): return empty dict on missing file
        project (Project): project to read config from (if level is project)
        verbose (int): print process data

    Returns:
        (dict): config yaml file contents
    """
    _yml = _get_cfg_yaml(
        level=level, namespace=namespace, verbose=verbose,
        project=project)
    if catch and not _yml.exists():
        return {}
    return _yml.read_yaml()


def set_cfg(data, namespace, level='code', project=None, verbose=0):
    """Write config to yaml file.

    Args:
        data (dict): config data
        namespace (str): namespace name to read from
        level (str): config level (eg. code/project)
        project (Project): project to read config from (if level is project)
        verbose (int): print process data
    """
    from psyhive import pipe

    _yml = _get_cfg_yaml(
        level=level, namespace=namespace, verbose=verbose, project=project)

    _data = {}
    _data.update(data)

    lprint('DATA:', _data)

    _existing_data = get_cfg(
        namespace=namespace, level=level, catch=True, project=project)
    if _existing_data == _data:
        lprint('NO UPDATE NEEDED')
        return
    elif _existing_data:
        lprint('EXISTING DATA:', _existing_data)
        _updated_data = _existing_data
        _updated_data.update(_data)
        lprint('UPDATED DATA:', _updated_data)
        _tmp = File('{}/tmp.yml'.format(pipe.TMP))
        lprint('TMP FILE:', _tmp.path)
        _tmp.write_yaml(_updated_data, force=True)
        _tmp.copy_to(_yml, diff_=True)
        raise NotImplementedError
    else:
        lprint('NO EXISTING DATA')

    _yml.write_yaml(_data)
