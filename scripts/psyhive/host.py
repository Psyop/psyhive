"""Tools for managing executing host across multiple host applications."""

from psyhive.utils import wrap_fn

NAME = None

try:
    from maya import cmds
except ImportError:
    pass
else:
    NAME = 'maya'
    cur_scene = wrap_fn(cmds.file, query=True, location=True)
    t_start = wrap_fn(cmds.playbackOptions, query=True, minTime=True)
    t_end = wrap_fn(cmds.playbackOptions, query=True, maxTime=True)


def t_range():
    """Get timeline range.

    Returns:
        (tuple): start/end time
    """
    return t_start(), t_end()


def t_frames():
    """Get a list of frames in the timeline.

    Returns:
        (int list): timeline frames
    """
    return range(int(t_start()), int(t_end())+1)
