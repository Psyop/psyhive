"""Tools for managing tank template representations."""

from psyhive import pipe, host
from psyhive.utils import find, get_single

from psyhive.tk2.tk_templates.tt_base import TTSequenceRoot, TTRoot, TTStepRoot
from psyhive.tk2.tk_templates.tt_work import TTWork
from psyhive.tk2.tk_templates.tt_output import TTOutput


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


def get_output(path):
    """Get output from the given path.

    Args:
        path (str): path to convert to output object

    Returns:
        (TTOutput): output tank template object
    """
    try:
        return TTOutput(path)
    except ValueError:
        return None


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
    try:
        return TTStepRoot(path)
    except ValueError as _exc:
        return None


def get_work(file_):
    """Get work file object associated with the given file.

    If an increment is passed, the associated work file is returned.

    Args:
        file_ (str): path to file

    Returns:
        (TTWork): work file
    """
    try:
        return TTWork(file_)
    except ValueError as _exc:
        return None
