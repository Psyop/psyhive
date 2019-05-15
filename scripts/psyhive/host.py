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
