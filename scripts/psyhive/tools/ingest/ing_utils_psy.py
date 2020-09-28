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


def map_ref_to_psy_asset(file_, query=True):
    """Map off pipeline reference path to a psyop file.

    Args:
        file_ (str): file to map
        query (bool): ask user to assign unmatched tags

    Returns:
        (str): path to psyop file
    """
    _file = File(abs_path(file_))

    print 'FILE', _file.path
    if _file.extn == 'mb' and _file.basename.startswith('camera_rig_main'):

        return tk2.find_asset('camera').find_step_root('rig').find_output_file(
            version='latest', format_='maya')
    assert query
    raise NotImplementedError
    # from . import _ing_vendor_file

    # if File(_file).extn not in ['ma', 'mb']:
    #     return

    # # Check for custom mapping
    # _proj = pipe.cur_project()
    # _mapping = _proj.cache_read('[INGEST] custom mapping') or {}
    # if _file in _mapping:
    #     _asset = tk2.TTAsset(_mapping[_file])
    #     _step = _asset.find_step_root('rig')
    #     return _step.find_output_file(
    #         extn='mb', format_='maya', version='latest',
    #         task='rig').path

    # try:
    #     _ref_file = _ing_vendor_file.VendorFile(file_)
    # except ValueError:
    #     return None

    # _out = _ref_file.to_psy_output_file(step='rig', query=query)
    # if not _out:
    #     return None

    # return _out.path
