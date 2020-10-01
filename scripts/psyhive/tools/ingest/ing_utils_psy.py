"""General utilities to aid ingestion."""

from psyhive import tk2, pipe, icons
from psyhive.utils import get_single, File, abs_path

ICON = icons.EMOJI.find("Fork and Knife With Plate")


def map_tag_to_asset(tag):
    """Map the given tag to an asset in the current project.

    Args:
        tag (str): tag to match

    Returns:
        (TTAsset): shot root
    """
    assert tag
    raise NotImplementedError


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


def map_file_to_psy_asset(file_, step='rig'):
    """Map off pipeline reference path to a psyop file.

    Args:
        file_ (str): file to map
        step (str): asset step

    Returns:
        (TTOutputFile): psyop asset file
    """
    from .. import ingest

    _file = File(abs_path(file_))
    if _file.extn == 'mb' and _file.basename.startswith('camera_rig_main'):
        _name = 'camera'
    elif ingest.is_vendor_file(file_):
        _file = ingest.VendorFile(file_)
        _name = _file.tag
    elif ingest.is_psy_asset(file_):
        _file = ingest.PsyAsset(file_)
        _name = _file.asset
    else:
        return None

    _asset = tk2.find_asset(asset=_name)
    _step = _asset.find_step_root(step)
    try:
        _file = _step.find_output_file(
            version='latest', format_='maya', task=step)
    except ValueError:
        raise ValueError('failed to find output file - '+_step.path)

    return _file
