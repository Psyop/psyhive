"""Tools for managing tank template representations."""

from psyhive import pipe, host
from psyhive.utils import find, get_single, passes_filter

from .tt_base import TTSequenceRoot, TTStepRoot, TTShot, TTAsset
from .tt_work import TTWork
from .tt_output import TTOutput, TTOutputFile, TTOutputFileSeq


def cur_shot():
    """Get current shot.

    Returns:
        (TTRoot|None): current shot (if any)
    """
    _work = cur_work()
    if not _work:
        return None
    return TTShot(_work.path)


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


def find_asset(filter_=None, asset=None, catch=False):
    """Find asset matching given filter.

    Args:
        filter_ (str): filter by path
        asset (str): filter by asset name
        catch (bool): no error on fail

    Returns:
        (TTAsset): matching asset root
    """
    _assets = find_assets()
    if filter_:
        _assets = [_asset for _asset in _assets
                   if passes_filter(_asset.path, filter_)]
    if asset:
        _assets = [_asset for _asset in _assets if _asset.asset == asset]
    return get_single(_assets, catch=catch, verbose=1)


def find_assets(filter_=None):
    """Read asset roots.

    Args:
        filter_ (str): filter by file path

    Returns:
        (TTAsset list): list of assets in this show
    """
    _root = pipe.cur_project().path+'/assets'
    _roots = []
    for _dir in find(_root, depth=3, type_='d', filter_=filter_):
        try:
            _asset = TTAsset(_dir)
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


def find_shot(name, catch=False, mode='disk'):
    """Find shot matching the given name.

    Args:
        name (str): name to search for
        catch (bool): no error if fail to match
        mode (str): where to search for shot (disk/sg)

    Returns:
        (TTRoot): matching shot
    """
    _shots = [_shot for _shot in find_shots(mode=mode) if _shot.name == name]
    if not _shots:
        raise ValueError('No {} shot found'.format(name))
    if len(_shots) > 1:
        raise ValueError('Multiple {} shots found'.format(name))
    return get_single(_shots, catch=catch)


def find_shots(class_=None, filter_=None, sequence=None, mode='disk'):
    """Find shots in the current job.

    Args:
        class_ (class): override shot root class
        filter_ (str): filter by shot name
        sequence (str): filter by sequence name
        mode (str): where to search for shot (disk/sg)

    Returns:
        (TTRoot): list of shots
    """
    if mode == 'disk':
        _seqs = find_sequences()
        if sequence:
            _seqs = [_seq for _seq in _seqs if _seq.name == sequence]
        return sum([
            _seq.find_shots(class_=class_, filter_=filter_)
            for _seq in _seqs], [])
    elif mode == 'sg':
        from psyhive import tk2
        _path_fmt = '{}/sequences/{}/{}'
        _shots = []
        for _seq in tk2.get_sg_data(
                type_='Sequence', fields=['shots', 'code'], limit=0):
            for _shot in _seq['shots']:
                _shot_path = _path_fmt.format(
                    pipe.cur_project().path, _seq['code'], _shot['name'])
                _shot = tk2.TTShot(_shot_path)
                _shots.append(_shot)
        return _shots
    else:
        raise ValueError(mode)


def get_asset(path):
    """Get an asset object from the given path.

    Args:
        path (str): path to test

    Returns:
        (TTAsset|None): shot root (if any)
    """
    try:
        _asset = TTAsset(path)
    except ValueError:
        return None
    if not _asset.asset:
        return None
    return _asset


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


def get_output_file(path):
    """Get output file or file seq from the given path.

    Args:
        path (str): path to convert

    Returns:
        (TTOutputFile|TTOutputFileSeq): output file or file seq
    """
    if '####' in path or '%04d' in path:
        return TTOutputFileSeq(path.replace('.####.', '.%04d.'))
    return TTOutputFile(path)


def get_shot(path):
    """Get a shot object from the given path.

    Args:
        path (str): path to test

    Returns:
        (TTShot|None): shot root (if any)
    """
    try:
        _root = TTShot(path)
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
