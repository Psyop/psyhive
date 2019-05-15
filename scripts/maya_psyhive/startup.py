"""Tools to be run on maya startup."""

import logging

from maya import cmds

from psyhive import icons, refresh
from psyhive.tools import track_usage
from psyhive.utils import dprint, wrap_fn, get_single, lprint
from maya_psyhive import ui
from maya_psyhive.tools import fkik_switcher

_BUTTONS = {
    'IKFK': {
        'cmd': '\n'.join([
            'import {} as fkik_switcher'.format(fkik_switcher.__name__),
            'fkik_switcher.launch_interface()']),
        'label': 'FK/IK switcher',
        'image': fkik_switcher.ICON},
}


def _add_elements_to_psyop_menu(verbose=0):
    """Add elements to psyop menu.

    Args:
        verbose (int): print process data
    """
    dprint('ADDING {:d} TO PSYOP MENU'.format(len(_BUTTONS)), verbose=verbose)
    _menu = ui.obtain_menu('Psyop')

    _anim = get_single([
        _child for _child in cmds.menu(_menu, query=True, itemArray=True)
        if cmds.menuItem(_child, query=True, label=True) == 'Animation'])

    for _name, _data in _BUTTONS.items():
        _mi_name = 'HIVE_'+_name
        if cmds.menuItem(_mi_name, query=True, exists=True):
            cmds.deleteUI(_mi_name)
        lprint(' - ADDING', _mi_name, verbose=verbose)
        cmds.menuItem(
            _mi_name, parent=_anim,
            command=_data['cmd'], image=_data['image'], label=_data['label'])


def _build_psyhive_menu():
    """Build psyhive menu."""
    _menu = ui.obtain_menu('PsyHive', replace=True)

    # Add FK/IK switcher
    for _name, _data in _BUTTONS.items():
        cmds.menuItem(
            command=_data['cmd'], image=_data['image'], label=_data['label'])

    # Add refresh
    _cmd = '\n'.join([
        'import {} as refresh'.format(refresh.__name__),
        'refresh.reload_libs(verbose=2)',
    ]).format()
    cmds.menuItem(
        label='Reload libs', command=_cmd,
        image=icons.EMOJI.find('Counterclockwise Arrows Button'))

    return _menu


@track_usage
def user_setup():
    """User setup."""
    dprint('Executing PsyHive user setup')

    if cmds.about(batch=True):
        return

    _build_psyhive_menu()

    # Fix logging level (pymel sets to debug)
    _fix_fn = wrap_fn(logging.getLogger().setLevel, logging.WARNING)
    cmds.evalDeferred(_fix_fn, lowestPriority=True)

    # Add elements to psyop menu (deferred to make sure exists)
    cmds.evalDeferred(_add_elements_to_psyop_menu, lowestPriority=True)
