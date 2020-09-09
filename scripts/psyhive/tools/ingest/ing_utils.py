"""General utilities to aid ingestion."""

from psyhive import tk2, pipe
from psyhive.utils import abs_path, get_single


def map_tag_to_shot(tag):
    """Map the given tag to a shot in the current project.

    Args:
        tag (str): tag to match

    Returns:
        (TTShot): shot root
    """

    # Try existing shot on disk
    _shot = tk2.find_shot(tag, catch=True)
    if _shot:
        return _shot

    # Try shot from sg
    _data = get_single(
        tk2.get_sg_data('Shot', code=tag, fields=['sg_sequence']),
        catch=True)
    if _data:
        _path = '{}/sequences/{}/{}'.format(
            pipe.cur_project().path, _data['sg_sequence']['name'], tag)
        return tk2.TTShot(_path)

    return None


def vendor_from_path(path):
    """Try to get vendor from the given delivery path.

    Args:
        path (str): path to read

    Returns:
        (str|None): vendor name (if any)
    """
    _tokens = abs_path(path).split('/')
    for _parent in ['vendor_in']:
        if _parent in _tokens and not _parent == _tokens[-1]:
            return _tokens[_tokens.index(_parent)+1]

    return None
