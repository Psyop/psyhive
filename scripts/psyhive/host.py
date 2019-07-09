"""Tools for managing executing host across multiple host applications."""

from psyhive.utils import wrap_fn

NAME = None


def refresh():
    """Refresh current dcc interface."""


try:
    from maya import cmds
except ImportError:
    pass
else:
    NAME = 'maya'
    batch_mode = wrap_fn(cmds.about, batch=True)
    cur_scene = wrap_fn(cmds.file, query=True, location=True)
    t_start = wrap_fn(cmds.playbackOptions, query=True, minTime=True)
    t_end = wrap_fn(cmds.playbackOptions, query=True, maxTime=True)
    refresh = cmds.refresh


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
