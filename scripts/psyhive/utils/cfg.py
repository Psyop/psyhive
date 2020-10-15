"""Tools for managing config files."""

import os

from .path import abs_path, File
from .misc import lprint


def _get_cfg_yaml(level, namespace, verbose=0):
    """Get path to config yaml file.

    Args:
        level (str): config level (eg. code/project)
        namespace (str): namespace name to read from
        verbose (int): print process data

    Returns:
        (File): config yaml
    """

    # Get path to yaml file
    if level == 'code':
        _yml = abs_path(
            '../../../cfg/{}.yml'.format(namespace),
            root=os.path.dirname(__file__))
    elif level == 'project':
        from psyhive import pipe
        _proj = pipe.cur_project()
        _yml = '{}/production/psyhive/cfg/{}.yml'.format(
            _proj.path, namespace)
    else:
        raise ValueError(level)
    lprint('YAML', _yml, verbose=verbose)
    return File(_yml)


def get_cfg(namespace, level='code', catch=False, verbose=0):
    """Read config from the given namespace.

    Args:
        namespace (str): namespace name to read from
        level (str): config level (eg. code/project)
        catch (bool): return empty dict on missing file
        verbose (int): print process data

    Returns:
        (dict): config yaml file contents
    """
    _yml = _get_cfg_yaml(level=level, namespace=namespace, verbose=verbose)
    if catch and not _yml.exists():
        return {}
    return _yml.read_yaml()


def set_cfg(data, namespace, level='code', verbose=0):
    """Write config to yaml file.

    Args:
        data (dict): config data
        namespace (str): namespace name to read from
        level (str): config level (eg. code/project)
        verbose (int): print process data
    """
    _yml = _get_cfg_yaml(level=level, namespace=namespace, verbose=verbose)

    _data = {}
    _data.update(data)

    lprint('DATA:', _data)

    _existing_data = get_cfg(namespace=namespace, level=level, catch=True)
    if _existing_data and not _existing_data == _data:
        # _yml.bkp_file()
        # Diff files
        # Config
        # Update existing data
        raise NotImplementedError

    _yml.write_yaml(_data)
