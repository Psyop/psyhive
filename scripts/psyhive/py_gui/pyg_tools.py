"""General tools for py_gui."""

from psyhive import host
from psyhive.utils import get_path


def build(mod, all_defs=True):
    """Build an interface for the given module.

    In maya it will build a MayaPyGui, otherwise it will build a QtPyGui.

    Args:
        mod (module): module to build gui from
        all_defs (bool): build all defs (not just install_gui decorated ones)

    Returns:
        (BasePyGui): interface instance
    """
    _file = get_path(mod).replace('.pyc', '.py')
    if host.NAME == 'maya':
        from .pyg_maya import MayaPyGui as _class
    else:
        from .pyg_qt import QtPyGui as _class
    return _class(_file, all_defs=all_defs)
