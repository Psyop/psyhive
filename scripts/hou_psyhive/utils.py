"""General utilies for houdini."""

import hou

from psyhive.utils import get_path, File, abs_path, dprint


def save_as(file_, revert_filename=True, force=False, verbose=0):
    """Save the current scene at the given path without changing cur filename.

    Args:
        file_ (str): path to save file to
        revert_filename (bool): disable revert filename
        force (bool): overwrite with no confirmation
        verbose (int): print process data
    """
    _cur_filename = hou.hipFile.name()

    # Test file paths
    _file = File(abs_path(get_path(file_)))
    _file.delete(wording='replace existing', force=force)

    # Execute save
    _file.test_dir()
    hou.hipFile.save(_file.path)
    dprint('SAVED SCENE', _file.nice_size(), _file.path, verbose=verbose)

    if revert_filename:
        hou.hipFile.setName(_cur_filename)
