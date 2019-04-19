"""Tools to be run on maya startup."""

import logging

from maya import cmds

from psyhive import icons, refresh
from psyhive.utils import dprint, wrap_fn
from maya_psyhive import ui
from maya_psyhive.tools import fkik_switcher


def _build_psyhive_menu():
    """Build psyhive menu."""
    _menu = ui.obtain_menu('PsyHive', replace=True)

    # Add FK/IK switcher
    _cmd = '\n'.join([
        'import {} as fkik_switcher'.format(fkik_switcher.__name__),
        'fkik_switcher.launch_interface()'])
    cmds.menuItem(
        label='FK/IK switcher', command=_cmd,
        image=icons.EMOJI.find('Left-Right Arrow'))

    # Add refresh
    _cmd = '\n'.join([
        'import {} as refresh'.format(refresh.__name__),
        'refresh.reload_libs(verbose=2)',
    ]).format()
    cmds.menuItem(
        label='Reload libs', command=_cmd,
        image=icons.EMOJI.find('Counterclockwise Arrows Button'))

    return _menu


def user_setup():
    """User setup."""
    dprint('Executing PsyHive user setup')

    _build_psyhive_menu()

    # Fix logging level (pymel sets to debug)
    _fix_fn = wrap_fn(logging.getLogger().setLevel, logging.WARNING)
    cmds.evalDeferred(_fix_fn, lowestPriority=True)
