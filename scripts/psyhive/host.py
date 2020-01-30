"""Tools for managing executing host across multiple host applications."""

from psyhive.utils import wrap_fn

NAME = None


def batch_mode():
    """Test for host being in batch mode (always False with no host).

    Returns:
        (bool): False
    """
    return False


def _get_cur_scene():
    """None if no dcc."""


def get_main_window_ptr():
    """None if no dcc."""


def refresh():
    """Refresh current dcc interface."""


try:
    from maya import cmds
except ImportError:
    pass
else:
    from maya_psyhive import ref, ui
    from maya_psyhive.utils import get_fps, save_as
    NAME = 'maya'
    batch_mode = wrap_fn(cmds.about, batch=True)
    _get_cur_scene = wrap_fn(cmds.file, query=True, location=True)
    _force_open_scene = lambda file_: cmds.file(file_, open=True, force=True)
    _force_new_scene = wrap_fn(cmds.file, new=True, force=True)
    refresh = cmds.refresh
    reference_scene = ref.create_ref
    save_scene = wrap_fn(cmds.file, save=True)
    _scene_modified = wrap_fn(cmds.file, query=True, modified=True)
    t_start = wrap_fn(cmds.playbackOptions, query=True, minTime=True)
    t_end = wrap_fn(cmds.playbackOptions, query=True, maxTime=True)
    set_start = wrap_fn(cmds.playbackOptions, arg_to_kwarg='minTime')
    set_end = wrap_fn(cmds.playbackOptions, arg_to_kwarg='maxTime')
    get_main_window_ptr = ui.get_main_window_ptr


if not NAME:
    try:
        import hou
    except ImportError:
        pass
    else:
        NAME = 'hou'
        _get_cur_scene = hou.hipFile.name

if not NAME:
    try:
        import unreal
    except ImportError:
        pass
    else:
        NAME = 'unreal'


def cur_scene():
    """Get the path to the current scene.

    Returns:
        (str|None): path to current scene (if any)
    """
    _cur_scene = _get_cur_scene()
    if _cur_scene == 'unknown':
        return None
    return _cur_scene


def _handle_unsaved_changes():
    """Handle unsaved changes in the current scene.

    If there are unsaved changes, offer to save or ignore them.
    """
    from psyhive import qt, icons

    _msg = 'Save changes to current scene?'

    _cur_scene = cur_scene()
    if _cur_scene:
        _msg += '\n\n{}'.format(_cur_scene)

    _result = qt.raise_dialog(
        _msg,
        title='Save changes',
        buttons=["Save", "Don't Save", "Cancel"],
        icon=icons.EMOJI.find('Octopus'))
    if _result == "Save":
        save_scene()
    elif _result == "Don't Save":
        pass
    else:
        raise ValueError(_result)


def open_scene(file_, force=False):
    """Open the given scene file.

    A warning is raised if the current scene has been modified.

    Args:
        file_ (str): file to open
        force (bool): lose current scene with no warning
    """
    if not force and _scene_modified():
        _handle_unsaved_changes()
    _force_open_scene(file_)


def new_scene(force=False):
    """Create a new scene.

    A warning is raised if the current scene has been modified.

    Args:
        force (bool): lose current scene with no warning
    """
    if not force and _scene_modified():
        _handle_unsaved_changes()
    _force_new_scene()


def set_range(start, end):
    """Set timeline range.

    Args:
        start (float): start frame
        end (float): end frame
    """
    set_start(start)
    set_end(end)


def t_range():
    """Get timeline range.

    Returns:
        (tuple): start/end time
    """
    return t_start(), t_end()


def t_frames(inc=1):
    """Get a list of frames in the timeline.

    Args:
        inc (int): frame increment

    Returns:
        (int list): timeline frames
    """
    return range(int(t_start()), int(t_end())+1, inc)
