"""General tools for managing yeti."""

import time

from maya import cmds

from psyhive.utils import get_single, Seq, lprint, seq_from_frame

from maya_psyhive import open_maya as hom


def apply_viewport_updates():
    """Create a script job that runs on timeline update.

    This will update all cache paths on yeti nodes to match the current frame
    every time the timeline is updated. The purpose of this is to allow yeti
    nodes that have been created on the fly to update in the viewport.
    """
    disable_viewport_updates()

    # Create new script job
    _cmd = time.strftime('\n'.join([
        '# PSYHIVE_YETI',
        'import {} as yeti'.format(__name__),
        'yeti.update_yeti_caches_to_cur_frame()',
    ]))
    _id = cmds.scriptJob(event=('timeChanged', _cmd), killWithScene=True)
    print 'CREATED SCRIPT JOB', _id


def disable_viewport_updates():
    """Remove any existing yeti viewport update script job."""

    # Kill existing script job
    _existing_job = get_single([
        _job for _job in cmds.scriptJob(listJobs=True)
        if 'PSYHIVE_YETI' in _job], catch=True)
    if _existing_job:
        _id = int(_existing_job.split(':')[0])
        print 'KILLING JOB', _id
        cmds.scriptJob(kill=_id)
    else:
        print 'NO EXISTING JOB FOUND'

    # Revert any yeti nodes to %04d style cache
    for _yeti in hom.CMDS.ls(type='pgYetiMaya'):
        _cache = _yeti.plug('cacheFileName').get_val()
        _seq = seq_from_frame(_cache, catch=True)
        if _seq:
            _yeti.plug('cacheFileName').set_val(_seq.path)


def update_yeti_caches_to_cur_frame(verbose=0):
    """Update yeti caches to point to the current frame.

    This is used in the script job which is triggered by timeline update.

    Args:
        verbose (int): print process data
    """
    _frame = int(round(cmds.currentTime(query=True)))
    lprint('UPDATE YETI CACHES', _frame, verbose=verbose)
    for _yeti in hom.CMDS.ls(type='pgYetiMaya'):
        print _yeti
        _file = _yeti.plug('cacheFileName').get_val()
        try:
            _seq = Seq(_file)
        except ValueError:
            _seq = seq_from_frame(_file)
        lprint(' -', _seq, verbose=verbose)
        _file = _seq[_frame]
        lprint(' -', _file, verbose=verbose)
        _yeti.plug('cacheFileName').set_val(_file)
