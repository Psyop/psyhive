"""Tools for managing tank template representations."""

from psyhive import pipe, host
from psyhive.utils import find, get_single

from psyhive.tk2.tk_templates.tt_base import TTSequenceRoot, TTRoot, TTStepRoot
from psyhive.tk2.tk_templates.tt_work import TTWork


def cur_shot():
    """Get current shot.

    Returns:
        (TTRoot|None): current shot (if any)
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
        (TTWork): work file
    """
    _cur_scene = host.cur_scene()
    if not _cur_scene:
        return None
    _class = class_ or TTWork
    try:
        return _class(_cur_scene)
    except ValueError:
        return None


def find_asset_roots():
    """Read asset roots."""
    _root = pipe.cur_project().path+'/assets'
    _roots = []
    for _dir in find(_root, depth=3, type_='d'):
        try:
            _asset = TTRoot(_dir)
        except ValueError:
            continue
        _roots.append(_asset)

    return _roots


def find_sequences():
    """Find sequences in the current project.

    Returns:
        (TTSequenceRoot): list of sequences
    """
    _seq_path = pipe.cur_project().path+'/sequences'
    _seqs = []
    for _path in find(_seq_path, depth=1):
        _seq = TTSequenceRoot(_path)
        _seqs.append(_seq)
    return _seqs


def find_shot(name):
    """Find shot matching the given name.

    Args:
        name (str): name to search for

    Returns:
        (TTRoot): matching shot
    """
    return get_single([
        _shot for _shot in find_shots() if _shot.name == name])


def find_shots(class_=None, filter_=None):
    """Find shots in the current job.

    Args:
        class_ (class): override shot root class
        filter_ (str): filter by shot name

    Returns:
        (TTRoot): list of shots
    """
    return sum([
        _seq.find_shots(class_=class_, filter_=filter_)
        for _seq in find_sequences()], [])


def get_shot(path):
    """Get a shot object from the given path.

    Args:
        path (str): path to test

    Returns:
        (TTRoot|None): shot root (if any)
    """
    try:
        _root = TTRoot(path)
    except ValueError:
        return None
    if not _root.shot:
        return None
    return _root


def get_step_root(path):
    """Get step root from the give path.

    Args:
        path (str): path to test

    Returns:
        (TTStepRoot|None): step root (if any)
    """
    return TTStepRoot(path)


def get_work(file_, class_=None, catch=True):
    """Get work file object associated with the given file.

    If an increment is passed, the associated work file is returned.

    Args:
        file_ (str): path to file
        class_ (type): force workfile type
        catch (bool): no error if no work file object was created

    Returns:
        (TTWork): work file
    """
    _class = class_ or TTWork
    try:
        return _class(file_)
    except ValueError as _exc:
        if catch:
            return None
        raise _exc
