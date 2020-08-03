"""General scene tools."""

from maya import cmds

from psyhive.utils import lprint, File, abs_path, dprint, get_path
from .mu_tools import load_plugin


def open_scene(file_, force=False, prompt=False, lazy=False, load_refs=True):
    """Open the given scene.

    Args:
        file_ (str): file to open
        force (bool): lose unsaved changes without confirmation
        prompt (bool): show missing reference dialogs
        lazy (bool): abandon load if scene is already open
        load_refs (bool): load references
    """
    from psyhive import host

    _file = get_path(file_)
    if lazy and host.cur_scene() == _file:
        return
    if not force:
        host.handle_unsaved_changes()
    if File(_file).extn == 'fbx':
        load_plugin('fbxmaya')

    _kwargs = {}
    if not load_refs:
        _kwargs['loadReferenceDepth'] = 'none'

    cmds.file(_file, open=True, force=True, prompt=prompt, ignoreVersion=True,
              **_kwargs)


def save_as(file_, revert_filename=True, export_selection=False, force=False,
            verbose=0):
    """Save the current scene at the given path without changing cur filename.

    Args:
        file_ (str): path to save file to
        revert_filename (bool): disable revert filename
        export_selection (bool): export selected nodes
        force (bool): overwrite with no confirmation
        verbose (int): print process data
    """
    _cur_filename = cmds.file(query=True, location=True)

    # Test file paths
    _file = File(abs_path(file_))
    _file.delete(wording='replace existing', force=force)

    # Execute save
    _file.test_dir()
    cmds.file(rename=_file.path)
    _kwargs = {
        'save' if not export_selection else 'exportSelected': True,
        'type': {'ma': 'mayaAscii', 'mb': 'mayaBinary'}[_file.extn]}
    cmds.file(options="v=0;", **_kwargs)
    dprint('SAVED SCENE', _file.nice_size(), _file.path, verbose=verbose)
    lprint(' - KWARGS', _kwargs, verbose=verbose > 1)

    if revert_filename:
        cmds.file(rename=_cur_filename)


def save_scene(file_=None, force=False):
    """Save current scene.

    Args:
        file_ (str): path to save as
        force (bool): force overwrite existing
    """
    _file = file_ or cmds.file(query=True, location=True)
    save_as(_file, revert_filename=False, force=force)
