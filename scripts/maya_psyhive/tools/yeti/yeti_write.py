"""Tools for managing yeti caching."""

import os
import shutil
import tempfile

from maya import cmds

from psyhive import tk, host, qt, icons
from psyhive.utils import abs_path, Seq, safe_zip, lprint, Dir, dprint

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import restore_sel, restore_frame

from maya_psyhive.tools.yeti.yeti_read import apply_cache


@restore_frame
@restore_sel
def _cache_yetis(yetis, apply_on_complete=False, verbose=0):
    """Cache a list of yeti nodes.

    Args:
        yetis (HFnDependencyNode list): nodes to cache
        apply_on_complete (bool): apply cache on completion
        verbose (int): print process data
    """
    print 'CACHE YETIS', yetis
    _work = tk.cur_work()
    _yetis, _outs, _namespaces, _kwargs = _prepare_yetis_and_outputs(
        yetis=yetis, work=_work)

    # Get cache path - if multiple namespace need to cache to tmp
    _tmp_fmt = abs_path('{}/yetiTmp/<NAME>.%04d.cache'.format(
        tempfile.gettempdir()))
    if len(_yetis) > 1:
        _cache_path = _tmp_fmt
        _tmp_dir = Dir(os.path.dirname(_tmp_fmt))
        _tmp_dir.delete(force=True)
        _tmp_dir.test_path()
    else:
        assert len(_outs) == 1
        _cache_path = _outs[0].path
    print "CACHE PATH", _cache_path

    # Generate caches
    dprint('GENERATING CACHES', _cache_path)
    for _yeti in _yetis:
        _yeti.plug('cacheFileName').set_val('')
        _yeti.plug('fileMode').set_val(0)
        _yeti.plug('overrideCacheWithInputs').set_val(False)
    cmds.select(_yetis)
    cmds.pgYetiCommand(
        writeCache=_cache_path, range=host.t_range(), samples=3)
    dprint('GENERATED CACHES', _cache_path)

    # Move tmp caches to outputs
    if len(_yetis) > 1:
        dprint('MOVING CACHES FROM TMP')
        for _yeti, _out in safe_zip(_yetis, _outs):
            print ' - MOVING', _out.path
            _name = str(_yeti).replace(":", "_")
            _tmp_seq = Seq(_tmp_fmt.replace('<NAME>', _name))
            for _frame, _tmp_path in safe_zip(
                    _tmp_seq.get_frames(), _tmp_seq.get_paths()):
                lprint('   -', _frame, _tmp_path, verbose=verbose)
                shutil.move(_tmp_path, _out[_frame])

    # Apply cache to yeti nodes
    if apply_on_complete:
        dprint('APPLYING CACHES TO YETIS')
        for _yeti, _cache in safe_zip(_yetis, _outs):
            apply_cache(cache=_cache, yeti=_yeti)


def _prepare_yetis_and_outputs(yetis, work):
    """Make sure all yetis are yeti shapes nodes and warn on output overwrite.

    Args:
        yetis (HFnDependencyNode list): nodes to cache
        work (TTWorkFileBase): work file being cached from

    Returns:
        (tuple): yeti nodes, outputs, namespaces, kwargs
    """
    _outs = []
    _namespaces = set()
    _force = False
    _yetis = []
    _kwargs = dict(format='yeti', output_type='fxcache', extension='fur')

    # Test outputs + tmp dirs
    for _yeti in yetis:

        if _yeti.object_type() == 'transform':
            _yeti = _yeti.shp
        _yetis.append(_yeti)

        # Map yeti node to output
        _namespaces.add(_yeti.namespace)
        _ref = ref.find_ref(_yeti.namespace)
        _out = work.map_to(
            work.output_file_seq_type,
            output_name='{}Yeti_{}'.format(
                _ref.namespace, _yeti.get_parent().clean_name),
            **_kwargs)
        _out.test_dir()
        _outs.append(_out)
        print ' - OUT', _out

        # Warn on replace existing
        if _out.exists():

            # Get dialog result
            _buttons = ['Yes', 'Cancel']
            if len(yetis) > 1:
                _buttons.insert(1, 'Yes to all')
            _start, _end = _out.find_range()
            _result = 'Yes' if _force else qt.raise_dialog(
                'Replace existing {} cache ({:d}-{:d})?\n\n{}'.format(
                    _yeti, _start, _end, _out.path),
                title='Replace existing', buttons=_buttons,
                icon=icons.EMOJI.find("Ghost"))

            # Apply result
            if _result == 'Yes to all':
                _force = True
            elif _result == 'Yes':
                pass
            else:
                raise qt.DialogCancelled

            _out.delete(force=True)

    return _yetis, _outs, _namespaces, _kwargs


def write_cache_from_sel_assets(apply_on_complete=False):
    """Cache selected asset.

    All yeti nodes in the asset are cached.

    The asset can be selected by selecting any node in the reference.

    Args:
        apply_on_complete (bool): apply cache on completion
    """
    _refs = ref.get_selected(multi=True)
    if not _refs:
        qt.notify_warning("No assets selected.\n\nPlease select the assets "
                          "you want to cache.")
        return
    print 'REFS', _refs

    # Get yeti nodes
    _yetis = sum([_ref.find_nodes(type_='pgYetiMaya') for _ref in _refs], [])

    if not _yetis:
        qt.notify_warning(
            "No yeti nodes in assets:\n\n    {}\n\nNone of these assets can "
            "be cached.".format('\n    '.join([
                _ref.namespace for _ref in _refs])))
        return

    _cache_yetis(_yetis, apply_on_complete=apply_on_complete)


def write_cache_from_sel_yetis(apply_on_complete=False):
    """Write a yeti cache from selected yeti nodes.

    Args:
        apply_on_complete (bool): apply cache on completion
    """
    _yetis = hom.get_selected(type_='pgYetiMaya', multi=True)
    if not _yetis:
        qt.notify_warning("No yeti nodes selected.\n\nPlease select one or "
                          "more yeti nodes.")
        return
    _cache_yetis(_yetis, apply_on_complete=apply_on_complete)


def write_cache_from_all_yetis(apply_on_complete=False):
    """Write a yeti cache from all yeti nodes in the scene.

    Args:
        apply_on_complete (bool): apply cache on completion
    """
    _yetis = hom.CMDS.ls(type='pgYetiMaya')
    if not _yetis:
        qt.notify_warning("No yeti nodes in the scene.\n\nUnable to cache.")
        return
    _cache_yetis(_yetis, apply_on_complete=apply_on_complete)
