"""Tools relating to tank templates."""

from psyhive import host
from psyhive.utils import File, lprint

from psyhive.tk.templates.tt_assets import (
    TTMayaAssetIncrement, TTMayaAssetWork,
    TTAssetStepRoot, TTAssetOutputFile)
from psyhive.tk.templates.tt_shots import (
    TTMayaShotIncrement, TTMayaShotWork,
    TTNukeShotIncrement, TTNukeShotWork,
    TTHoudiniShotIncrement, TTHoudiniShotWork,
    get_shot, TTShotStepRoot, TTShotOutputFile, TTShotOutputFileSeq)


def cur_shot():
    """Get current shot.

    Returns:
        (TTShotRoot|None): current shot (if any)
    """
    _work = cur_work()
    if not _work:
        return None
    return _work.shot


def cur_work(class_=None):
    """Get work file object associated with the current file.

    Args:
        class_ (type): force workfile type

    Returns:
        (TTWorkFileBase): work file
    """
    _cur_scene = host.cur_scene()
    if not _cur_scene:
        return None
    return get_work(_cur_scene, class_=class_, catch=True)


def get_output(path):
    """Get output from the given path.

    Args:
        path (str): path to convert to output object

    Returns:
        (TTOutputFileBase): output tank template object
    """
    for _type in [TTAssetOutputFile, TTShotOutputFile, TTShotOutputFileSeq]:
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


def _get_work_type(file_, inc, catch):
    """Get work type for the given file.

    Args:
        file_ (File): file to test
        inc (bool): if file is an increment
        catch (bool): no error if no valid work could be found

    Returns:
        (class): work file type
    """
    _shot = get_shot(file_.path)

    if file_.extn in ['ma', 'mb']:
        if _shot:
            _class = TTMayaShotIncrement if inc else TTMayaShotWork
        else:
            _class = TTMayaAssetIncrement if inc else TTMayaAssetWork
    elif file_.extn in ['nk']:
        if _shot:
            _class = TTNukeShotIncrement if inc else TTNukeShotWork
        else:
            _class = TTNukeAssetIncrement if inc else TTNukeAssetWork
    elif file_.extn in ['hip']:
        if _shot:
            _class = TTHoudiniShotIncrement if inc else TTHoudiniShotWork
        else:
            _class = TTHoudiniAssetIncrement if inc else TTHoudiniAssetWork
    else:
        if catch:
            return None
        raise ValueError(file_)

    return _class


def get_work(file_, class_=None, catch=True, verbose=0):
    """Get work file object associated with the given file.

    If an increment is passed, the associated work file is returned.

    Args:
        file_ (str): path to file
        class_ (type): force workfile type
        catch (bool): no error if no valid work could be found
        verbose (int): print process data

    Returns:
        (TTWorkFileBase): work file
    """
    _file = File(file_)
    _inc = file_ and not _file.basename.split("_")[-1].startswith('v')

    # Get work file class
    if class_:
        _class = class_
    else:
        try:
            _class = _get_work_type(file_=_file, inc=_inc, catch=catch)
        except ValueError as _exc:
            if catch:
                return None
            raise _exc
    lprint("CLASS", _class, verbose=verbose)
    if not _class:
        return None

    if _inc:
        try:
            return _class(file_).get_work()
        except ValueError as _exc:
            if catch:
                return None
            raise _exc

    # Process file as work file
    try:
        return _class(file_)
    except ValueError as _exc:
        if catch:
            return None
        raise _exc
