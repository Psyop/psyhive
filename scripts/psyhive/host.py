"""Tools for managing executing host across multiple host applications."""

from psyhive.utils import wrap_fn, abs_path, get_path

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
    from maya_psyhive.utils import (
        get_fps, save_as, save_scene, open_scene as open_scene_)
    NAME = 'maya'
    batch_mode = wrap_fn(cmds.about, batch=True)
    _get_cur_scene = wrap_fn(cmds.file, query=True, location=True)
    _force_open_scene = lambda file_: open_scene_(file_, force=True)
    _force_new_scene = wrap_fn(cmds.file, new=True, force=True)
    refresh = cmds.refresh
    reference_scene = ref.create_ref
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
        get_fps = hou.fps
        get_main_window_ptr = hou.ui.mainQtWindow
        t_start = lambda: hou.playbar.frameRange()[0]
        t_end = lambda: hou.playbar.frameRange()[1]

if not NAME:
    try:
        import unreal
    except ImportError:
        pass
    else:
        NAME = 'unreal'


if not NAME:
    try:
        import nuke
    except ImportError:
        pass
    else:
        from nuke_psyhive.utils import open_scene as open_scene_
        NAME = 'nuke'
        _force_open_scene = lambda file_: open_scene_(file_, force=True)
        _get_cur_scene = nuke.Root()["name"].getValue
        _scene_modified = nuke.modified


def cur_scene():
    """Get the path to the current scene.

    Returns:
        (str|None): path to current scene (if any)
    """
    _cur_scene = _get_cur_scene()
    if not _cur_scene or _cur_scene == 'unknown':
        return None
    return abs_path(_cur_scene)


def handle_unsaved_changes(icon=None, parent=None):
    """Handle unsaved changes in the current scene.

    If there are unsaved changes, offer to save or ignore them.

    Args:
        icon (str): override dialog icon
        parent (QDialog): override dialog parent
    """
    from psyhive import qt, icons

    _msg = 'Save changes to current scene?'

    _cur_scene = cur_scene()
    if _cur_scene:
        _msg += '\n\n{}'.format(_cur_scene)

    _result = qt.raise_dialog(
        _msg, title='Save changes', parent=parent,
        buttons=["Save", "Don't Save", "Cancel"],
        icon=icon or icons.EMOJI.find('Octopus'))
    if _result == "Save":
        save_scene()
    elif _result == "Don't Save":
        pass
    else:
        raise ValueError(_result)


def open_scene(file_, func=None, force=False, lazy=False):
    """Open the given scene file.

    A warning is raised if the current scene has been modified.

    Args:
        file_ (str): file to open
        func (fn): override save function
        force (bool): lose current scene with no warning
        lazy (bool): abandon open scene if file is already open
    """
    _file = get_path(file_)
    if lazy and cur_scene() == _file:
        print 'SCENE ALREADY OPEN', _file
        return
    if not force and _scene_modified():
        handle_unsaved_changes()
    _func = func or wrap_fn(_force_open_scene, _file)
    _func()


def new_scene(force=False):
    """Create a new scene.

    A warning is raised if the current scene has been modified.

    Args:
        force (bool): lose current scene with no warning
    """
    if not force and _scene_modified():
        handle_unsaved_changes()
    _force_new_scene()


def set_range(start, end):
    """Set timeline range.

    Args:
        start (float): start frame
        end (float): end frame
    """
    set_start(start)
    set_end(end)


def t_range(class_=None):
    """Get timeline range.

    Args:
        class_ (class): override class (eg. int)

    Returns:
        (tuple): start/end time
    """
    _vals = t_start(), t_end()
    if class_:
        _vals = tuple([class_(_val) for _val in _vals])
    return _vals


def t_frames(inc=1):
    """Get a list of frames in the timeline.

    Args:
        inc (int): frame increment

    Returns:
        (int list): timeline frames
    """
    return range(int(t_start()), int(t_end())+1, inc)
