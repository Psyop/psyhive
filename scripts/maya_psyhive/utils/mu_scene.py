"""General scene tools."""

from maya import cmds

from psyhive.utils import lprint, File, abs_path, dprint, get_path
from .mu_tools import load_plugin, mel_


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


def save_abc(
        file_, objs=None, rng=None, step_size=1.0, user_attr_prefixes=(),
        mode='export', format_='ogawa', no_normals=False, uv_write=True,
        write_face_sets=True, selection=False):
    """Save an abc to disk.

    Args:
        file_ (str): path to save to
        objs (str list): objects to save
        rng (tuple): export frame range
        step_size (float): step size in frames
        user_attr_prefixes (tuple): user attribute prefix list
        mode (str): export mode
            export - export the abc
            job_str - just return the job string
        format_ (str): abc format
        no_normals (bool): add -noNormals flag
        uv_write (bool): add -uvWrite flag
        write_face_sets (bool): add -writeFaceSets flag
        selection (bool): export selection

    Returns:
        (str): job string (if mode is job_str)
    """
    from psyhive import host

    if not (objs or selection):
        raise RuntimeError('Nothing to export')

    # Process flags
    _objs_str = ""
    if objs:
        _objs_str = "-root " + " -root ".join(map(str, objs))
    _uap_str = ""
    for _uap in user_attr_prefixes:
        _uap_str += " -userAttrPrefix "+_uap
    _start, _end = rng or host.t_range(int)

    # Build job str
    _job_str = (
        "-frameRange {start:d} {end:d} "
        "-dataFormat {format} "
        "-step {step} "
        "-worldSpace "
        "{no_normals} {uv_write} {write_face_sets} {selection}"
        "{user_attr_prefixes} "
        "-file {file} "
        "{roots_str} ".format(
            start=_start, end=_end, step=step_size,
            file=abs_path(file_), format=format_,
            roots_str=_objs_str,
            no_normals='-noNormals' if no_normals else '',
            uv_write='-uvWrite' if uv_write else '',
            write_face_sets='-writeFaceSets' if write_face_sets else '',
            selection='-selection' if selection else '',
            user_attr_prefixes=_uap_str))
    while '  ' in _job_str:
        _job_str = _job_str.replace('  ', ' ')

    # Execute
    if mode == 'job_str':
        return _job_str
    elif mode == 'export':
        cmds.loadPlugin('AbcExport', quiet=True)
        File(file_).test_dir()
        _mel = 'AbcExport -jobArg "{}"'.format(_job_str)
        mel_(_mel)
    else:
        raise ValueError(mode)


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


def save_scene(file_=None, export_selection=False, force=False):
    """Save current scene.

    Args:
        file_ (str): path to save as
        export_selection (bool): export selected nodes
        force (bool): overwrite with no confirmation
    """
    _file = file_ or cmds.file(query=True, location=True)
    save_as(_file, revert_filename=False, force=force,
            export_selection=export_selection)
