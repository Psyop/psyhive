"""Tools relating to tank templates."""

from psyhive import host
from psyhive.utils import File

from psyhive.tk.templates.shots import TTMayaShotIncrement, TTMayaShotWork


def get_work(file_, class_=None):
    """Get work file object associated with the given file.

    If an increment is passed, the associated work file is returned.

    Args:
        file_ (str): path to file
        class_ (type): force workfile type

    Returns:
        (TTWorkFileBase): work file
    """
    _file = File(file_)
    _inc = not _file.basename.split("_")[-1].startswith('v')

    if class_:
        _class = class_
    elif _file.extn == 'ma':
        _class = TTMayaShotIncrement if _inc else TTMayaShotWork
    else:
        raise ValueError(file_)

    if _inc:
        return _class(file_).get_work()

    return _class(file_)


def cur_work(class_=None):
    """Get work file object associated with the current file.

    Args:
        class_ (type): force workfile type

    Returns:
        (TTWorkFileBase): work file
    """
    return get_work(host.cur_scene(), class_=class_)
