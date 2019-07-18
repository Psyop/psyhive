"""Tools relating to tank templates."""

from psyhive import host
from psyhive.utils import File

from psyhive.tk.templates.assets import (
    TTMayaAssetIncrement, TTMayaAssetWork, TTAssetStepRoot,
    TTAssetOutputFile)
from psyhive.tk.templates.shots import (
    TTMayaShotIncrement, TTMayaShotWork, get_shot, TTShotStepRoot,
    TTShotOutputFile)


def get_output(path):
    """Get output from the given path.

    Args:
        path (str): path to convert to output object

    Returns:
        (TTOutputFileBase): output tank template object
    """
    for _type in [TTAssetOutputFile, TTShotOutputFile]:
        try:
            return _type(path)
        except ValueError:
            pass
    return None


def get_step_root(path, catch=True):
    """Get step root from the give path.

    Args:
        path (str): path to test
        catch (bool): no error on fail

    Returns:
        (TTStepRootBase|None): step root (if any)
    """
    for _class in [TTShotStepRoot, TTAssetStepRoot]:
        try:
            return _class(path)
        except ValueError:
            continue
    if catch:
        return None
    raise ValueError(path)


def get_work(file_, class_=None, catch=True):
    """Get work file object associated with the given file.

    If an increment is passed, the associated work file is returned.

    Args:
        file_ (str): path to file
        class_ (type): force workfile type
        catch (bool): no error if no valid work could be found

    Returns:
        (TTWorkFileBase): work file
    """
    _file = File(file_)
    _inc = not _file.basename.split("_")[-1].startswith('v')
    _shot = get_shot(file_)

    if class_:
        _class = class_
    elif _file.extn in ['ma', 'mb']:
        if _shot:
            _class = TTMayaShotIncrement if _inc else TTMayaShotWork
        else:
            _class = TTMayaAssetIncrement if _inc else TTMayaAssetWork
    else:
        if catch:
            return None
        raise ValueError(file_)

    if _inc:
        return _class(file_).get_work()

    try:
        return _class(file_)
    except ValueError as _exc:
        if catch:
            return None
        raise _exc


def cur_work(class_=None):
    """Get work file object associated with the current file.

    Args:
        class_ (type): force workfile type

    Returns:
        (TTWorkFileBase): work file
    """
    _cur_scene = host.cur_scene()
    if not _cur_scene:
        return _cur_scene
    return get_work(_cur_scene, class_=class_)
