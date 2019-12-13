"""Tools for TechAnim."""

import os

from maya import cmds, mel
from maya.app.general import createImageFormats

from psyhive import tk2, icons, host, qt, py_gui
from psyhive.utils import File, abs_path, lprint, store_result

from maya_psyhive import open_maya as hom

ICON = icons.EMOJI.find('Banana')
PYGUI_TITLE = 'TechAnim Tools'


class _Action(object):
    """Enum for cache action."""

    ADD = "add"
    REPLACE = "replace"
    MERGE = "merge"
    MERGE_DELETE = "mergeDelete"


class _FileMode(object):
    """Enum for cache file mode."""

    ONE_FILE = "OneFile"
    ONE_FILE_PER_FRAME = "OneFilePerFrame"


class _NCloth(hom.HFnDependencyNode):
    """Represents an nCloth node."""

    def get_cache_xml(self):
        """Get cache xml file for the current workspace.

        Returns:
            (File): cache xml file
        """
        _work = tk2.cur_work()
        _cache_xml = File('{}/cache/nCache/{}/{}.xml'.format(
            _work.get_work_area().path, _work.basename, self))
        return _cache_xml

    def delete_cache(self, force=False):
        """Delete existing caches in the current workspace.

        Args:
            force (bool): delete with no confirmation
        """
        _cache_xml = self.get_cache_xml()
        _cache_xml.parent().delete(force=force, wording='replace')


def _get_blast_seq():
    """Get blast image sequence for the current workspace.

    Returns:
        (Seq): blast/capture sequence
    """
    _cam = hom.get_active_cam()
    _work = tk2.cur_work()
    return _work.map_to(
        tk2.TTOutputFileSeq, output_type='capture', format='jpg',
        extension='jpg', output_name=str(_cam))


def _do_create_cache(
        start, end, file_mode=_FileMode.ONE_FILE_PER_FRAME,
        update_viewport=True, cache_dir='', cache_per_geo=False, cache_name='',
        cache_name_as_prefix=False, action=_Action.ADD, force_save=True,
        sim_rate=1, sample_mult=1, inherit_settings=False, use_float=True,
        verbose=0):
    """Create an nCloth cache.

    Args:
        start (int): start frame
        end (int): end frame
        file_mode (FileMode): file mode
        update_viewport (bool): update viewport on cache
        cache_dir (str): force cache dir (empty to use default)
        cache_per_geo (bool): generate cache xml per geo
        cache_name (str): name of cache (normally nCloth shape name)
        cache_name_as_prefix (bool): use cache name as prefix
        action (Action): cache action
        force_save (bool): force save even if it overwrites existing files
        sim_rate (int): the rate at which the cloth simulation is
            forced to run
        sample_mult (int): the rate at which samples are written, as
            a multiple of simulation rate.
        inherit_settings (bool): whether modifications should be
            inherited from the cache about to be replaced
        use_float (bool): whether to store doubles as floats
        verbose (int): print process data
    """
    _source_custom_n_cache()

    _start = int(host.t_start())
    _end = int(host.t_end())
    _work = tk2.cur_work()

    _args = [None] * 16
    _args[0] = 0  # time_range_mode - use args 1/2
    _args[1] = start
    _args[2] = end
    _args[3] = file_mode
    _args[4] = int(update_viewport)
    _args[5] = cache_dir
    _args[6] = int(cache_per_geo)
    _args[7] = cache_name
    _args[8] = int(cache_name_as_prefix)
    _args[9] = action
    _args[10] = int(force_save)
    _args[11] = sim_rate
    _args[12] = sample_mult
    _args[13] = int(inherit_settings)
    _args[14] = int(use_float)
    _args[15] = "mcx"

    _cmd = 'doCreateNclothCache 5 {{ {} }};'.format(', '.join([
        '"{}"'.format(_arg) for _arg in _args]))
    lprint(_cmd, verbose=verbose)
    mel.eval(_cmd)


def _update_xml_start_frames(n_cloths=None, force=True):
    """Update start frames in cache xml file.

    As the cache is run on individual frames, the xml file is regenrated
    on each frame as a one frame cache. This means the start frame needs
    to be updated but also the sample rate which is written as zero for
    one frame caches. Loading a cache with zero sample rate and a frame
    range will make maya seg fault.

    Args:
        n_cloths (NCloth list): nCloth caches to update
        force (bool): update without confirmation
    """
    _start, _end = host.t_range()
    _start_tick, _end_tick = int(_start*240), int(_end*240)
    _n_cloths = n_cloths or [_NCloth(_n_cloth)
                             for _n_cloth in cmds.ls(type='nCloth')]
    for _n_cloth in _n_cloths:
        _xml = _n_cloth.get_cache_xml()
        print _n_cloth, _xml.path
        assert _xml.exists()
        _body = _xml.read()
        for _str in [
                'Range="{start}-{end}"',
                'StartTime="{start}"',
                'SamplingRate="{rate}"',
        ]:
            _find = _str.format(start=_end_tick, end=_end_tick, rate=0)
            _replace = _str.format(start=_start_tick, end=_end_tick, rate=240)
            assert _body.count(_find) == 1
            _body = _body.replace(_find, _replace)
        _xml.write_text(_body, force=force)


def _mel(mel_):
    """Execute mel and print the code being executed.

    Args:
        mel_ (str): mel to execute
    """
    print mel_
    mel.eval(mel_)


def _attach_caches(n_cloths=None):
    """Attach caches to the given nCloth nodes.

    Args:
        n_cloths (NCloth list): nodes to attach caches to
    """
    _source_custom_n_cache()

    _n_cloths = n_cloths or [_NCloth(_n_cloth)
                             for _n_cloth in cmds.ls(type='nCloth')]
    for _n_cloth in _n_cloths:
        cmds.select(_n_cloth)
        _mel('string $cacheFiles[] = {{"{}"}};'.format(_n_cloth))
        _mel('string $objsToCache[] = {{"{}"}};'.format(_n_cloth))
        _mel('string $cacheDirectory = "{}";'.format(
            _n_cloth.get_cache_xml().dir))
        _mel('string $replaceMode = "replace";')
        _mel('attachOneCachePerGeometry($cacheFiles, $objsToCache, '
             '$cacheDirectory, $replaceMode);')
        print


@store_result
def _source_custom_n_cache():
    """Source the custom doCreateNclothCache mel.

    This overrides the built in maya doCreateNclothCache function, which
    doesn't all the caches NOT to be attached each time it's run. If updating
    to a new maya version, it's prob a good idea to compare this file to
    maya's declaration to make sure the function hasn't changed.

    This only needs to be sourced once.
    """
    _file = abs_path(
        '{}/_doCreateNclothCache.mel'.format(os.path.dirname(__file__)))
    assert os.path.exists(_file)
    print 'SOURCING', _file
    mel.eval('source "{}";'.format(_file))


def _blast(start, end, res, verbose=0):
    """Execute a playblast.

    Args:
        start (int): start frame
        end (int): end frame
        res (tuple): override image resolution
        verbose (int): print process data
    """
    _seq = _get_blast_seq()
    if res:
        _width, _height = res
    else:
        _width = cmds.getAttr('defaultResolution.width')
        _height = cmds.getAttr('defaultResolution.height')
    lprint('RES', _width, _height, verbose=verbose)

    # Set image format
    _fmt_mgr = createImageFormats.ImageFormats()
    _fmt_mgr.pushRenderGlobalsForDesc({
        'jpg': "JPEG",
        'exr': "EXR",
    }[_seq.extn])

    _filename = '{}/{}'.format(_seq.dir, _seq.basename)
    cmds.playblast(
        startTime=start, endTime=end, format='image', filename=_filename,
        viewer=False, width=_width, height=_height, offScreen=True,
        percent=100)

    _fmt_mgr.popRenderGlobals()


@py_gui.install_gui(
    label='Blast and nCache', label_width=90,
    choices={'resolution': ['720x576', '1020x720', 'Use render globals']})
def blast_and_cache(
        force_overwrite=False, attach_cache=True, view_blast=True,
        resolution=None):
    """Execute playblast and cache nCloth nodes.

    This allows blasting and caching to happen with a single pass of
    the timeline. Any nCloth nodes that are not enabled are ignored.

    Args:
        force_overwrite (bool): overwrite any existing blasts/caches
            with no confirmation dialog
        attach_cache (bool): attach the caches on completion
        view_blast (bool): view playblast on completion
        resolution (str): blast resolution
    """

    # Get blast resolution
    _res = (None if 'x' not in resolution
            else [int(_val) for _val in resolution.split('x')])

    # Get nCloth nodes
    _n_cloths = [_NCloth(str(_n_cloth))
                 for _n_cloth in hom.CMDS.ls(type='nCloth')
                 if _n_cloth.plug('isDynamic').get_val()]
    print 'NCLOTH NODES:', _n_cloths

    # Delete existing
    for _n_cloth in _n_cloths:
        _n_cloth.delete_cache(force=force_overwrite)
    _seq = _get_blast_seq()
    _seq.delete(force=force_overwrite, wording='replace')

    # Execute cache/blast
    _frames = host.t_frames()
    for _idx, _frame in qt.progress_bar(
            enumerate(_frames), 'Blasting/caching {:d} frame{}',
            col='PowderBlue'):
        _action = _Action.REPLACE
        for _n_cloth in _n_cloths:
            cmds.select(_n_cloth)
            _do_create_cache(start=_frame, end=_frame, action=_action)
            assert _n_cloth.get_cache_xml().exists()
        _blast(start=_frame, end=_frame, res=_res)

    if view_blast:
        _seq.view()
    if attach_cache:
        _update_xml_start_frames(n_cloths=_n_cloths, force=True)
        _attach_caches(n_cloths=_n_cloths)
