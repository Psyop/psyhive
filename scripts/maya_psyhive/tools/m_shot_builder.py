"""Tools for building updating a template file to a different shot."""

from psyhive import tk, host, qt
from psyhive.utils import dprint, lprint
from maya_psyhive import open_maya as hom
from maya_psyhive import ref


def build_shot_from_template(shot, template, force=False):
    """Build a scene from the given template.

    Args:
        shot (str): name of shot to update to (eg. rnd0080)
        template (str): path to template work file
        force (bool): force save new scene with no confirmation
    """
    _shot = tk.find_shot(shot)
    _tmpl_work = tk.get_work(template)
    if not host.cur_scene() == _tmpl_work.path:
        _tmpl_work.load()

    _update_assets()
    _update_abcs(shot=shot)

    # Update frame range
    _rng = _shot.get_frame_range()
    print 'RANGE', _rng
    host.set_range(*_rng)

    # Save scene
    _shot_work = _tmpl_work.map_to(Shot=_shot.name).find_next()
    print 'SHOT WORK', _shot_work
    if not force:
        qt.ok_cancel("Save new work file?\n\n"+_shot_work.path)
    _shot_work.save(comment='Scene built by shot_builder')


def _update_assets(verbose=0):
    """Update scene assets to latest version.

    Args:
        verbose (int): print process data
    """
    dprint('UPDATING ASSETS')
    for _ref in qt.progress_bar(ref.find_refs(), 'Updating {:d} asset{}'):

        # Find asset
        _asset = tk.get_output(_ref.path)
        if not _asset:
            continue

        # Make sure asset is latest
        if not _asset.is_latest():
            _latest = _asset.find_latest()
            lprint(' - UPDATING TO LATEST: {}'.format(_latest.path),
                   verbose=verbose)
            _ref.swap_to(_latest.path)
            _status = 'updated'
        else:
            _status = 'no update needed'
        print ' - {:25} {:20} {}'.format(_ref.namespace, _status, _asset.path)
    print


def _update_abcs(shot='rnd0080', verbose=0):
    """Update abcs to point to the given shot.

    Args:
        shot (str): name of shot to update to (eg. rnd0080)
        verbose (int): print process data
    """

    dprint('CHECKING ABCS')
    _refs_to_remove = set()
    for _exo in qt.progress_bar(
            hom.CMDS.ls(type='ExocortexAlembicFile'), 'Updating {:d} abc{}'):
        lprint('CHECKING EXO', _exo, verbose=verbose)
        _path = _exo.plug('fileName').get_val()
        _status, _to_remove = _update_abc(exo=_exo, shot=shot, verbose=verbose)
        if _to_remove:
            _refs_to_remove.add(_to_remove)
        print ' - {:60} {:30} {}'.format(_exo, _status, _path)
    print

    if _refs_to_remove:
        dprint('REMOVING {:d} REFS WITH NO {} CACHES'.format(
            len(_refs_to_remove), shot))
        for _ref in _refs_to_remove:
            _ref.remove(force=True)


def _update_abc(exo, shot, verbose=0):
    """Update abc to point to the given shot.

    Args:
        exo (HFnDependencyNode): exocortex abc node
        shot (str): name of shot to update to (eg. rnd0080)
        verbose (int): print process data

    Returns:
        (tuple): update status, ref to remove (if any)
    """
    _ref = (
        ref.find_ref(namespace=exo.namespace, catch=True)
        if exo.namespace else None)
    lprint(' - REF', _ref, verbose=verbose)
    _tmpl_abc = exo.plug('fileName').get_val()
    _tmpl_output = tk.get_output(_tmpl_abc)
    if not _tmpl_output or not _tmpl_output.shot:
        lprint(' - NO OUTPUT FOUND', exo, _tmpl_abc, verbose=verbose)
        return 'off pipeline', None
    if _tmpl_output.shot.name == shot:
        lprint(' - NO UPDATE NEEDED', _tmpl_abc, verbose=verbose)
        return 'no update needed', None

    # Map to this shot
    lprint(' - TMPL ABC', _tmpl_abc, verbose=verbose)
    _shot_output = _tmpl_output.map_to(
        type(_tmpl_output), Shot=shot)
    try:
        _shot_output = _shot_output.find_latest()
    except OSError:
        lprint(' - NO VERSIONS FOUND', _shot_output, verbose=verbose)
        return 'no {} versions found'.format(shot), _ref

    # Update exocortex node
    lprint(' - SHOT ABC', _shot_output.path, verbose=verbose)
    exo.plug('fileName').set_val(_shot_output.path)
    return 'updated', None
