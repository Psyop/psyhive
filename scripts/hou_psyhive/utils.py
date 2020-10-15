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


def save_scene(file_, force=False):
    """Save current scene to the given path.

    Args:
        file_ (str): path to save file to
        force (bool): overwrite without confirmation
    """
    save_as(file_, revert_filename=False)


def set_end(frame):
    """Set timeline end frame.

    Args:
        frame (int): frame to apply
    """
    from psyhive import host
    _start, _ = host.t_range()
    hou.playbar.setFrameRange(_start, frame)


def set_start(frame):
    """Set timeline start frame.

    Args:
        frame (int): frame to apply
    """
    from psyhive import host
    _, _end = host.t_range()
    hou.playbar.setFrameRange(frame, _end)
