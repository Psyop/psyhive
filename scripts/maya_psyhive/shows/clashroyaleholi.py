"""Tools for Clash Royale Holdays project."""

import pprint

from psyhive import qt, py_gui, icons, tk2
from psyhive.tools import hive_bro
from psyhive.utils import lprint
from maya_psyhive import ref, tank_support

LABEL = "Clash Royale Holidays"
ICON = icons.EMOJI.find('Christmas Tree')


py_gui.install_gui('Crowd standins')


def _get_default_browser_dir(work=None, verbose=0):
    """Get default directory for file browser.

    Args:
        work (TTWork): override primary work
        verbose (int): print process data

    Returns:
        (str): browser dir
    """
    _works = [work] + [tk2.cur_work()] + hive_bro.get_recent_work()
    _shots = [_work.get_shot() for _work in _works
              if _work and _work.shot] + tk2.find_shots()
    _shots = [_shot for _idx, _shot in enumerate(_shots)
              if _shots.index(_shot) == _idx]
    if verbose:
        pprint.pprint(_works)
        pprint.pprint(_shots)

    _dir = None
    for _shot in _shots:
        _dir = _shot.find_step_root('animation').map_to(
            hint='shot_output_type', class_=tk2.TTOutputType,
            output_type='animcache', Task='animation')
        if not _dir.exists():
            lprint(' - MISSING', _dir, verbose=verbose)
            continue
        lprint(' - MATCHED', _dir, verbose=verbose)
        return _dir.path

    return None


@py_gui.install_gui(
    label='Create aiStandIn from selected shade',
    browser={'archive': py_gui.BrowserLauncher(
        get_default_dir=_get_default_browser_dir, title='Select archive')},
    hide=['verbose'])
def create_standin_from_sel_shade(
        archive=('P:/projects/clashroyale2019_34814P/sequences/'
                 'crowdCycles25Fps/cid00Aid001/animation/output/animcache/'
                 'animation_archer/v014/'
                 'alembic/cid00Aid001_animation_archer_v014.abc'),
        verbose=0):
    """Create aiStandIn from selected shade asset.

    The shader is read from all mesh nodes in the shade asset, and then this
    is used to create an aiSetParameter node on the standin for each shader.
    If all the meshes using the shader has matching values for ai attrs,
    these values are applied as overrides on the aiSetParameter node.

    Args:
        archive (str): path to archive to apply to standin
        verbose (int): print process data
    """
    _shade = ref.get_selected(catch=True)
    if not _shade:
        qt.notify_warning('No shade asset selected.\n\nPlease select a shade '
                          'asset to read shaders from.')
        return
    tank_support.build_aistandin_from_shade(
        shade=_shade, verbose=verbose, archive=archive)
