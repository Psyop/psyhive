"""General utilities to aid ingestion."""

from psyhive import tk2, pipe, icons
from psyhive.utils import get_single

ICON = icons.EMOJI.find("Fork and Knife With Plate")


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
