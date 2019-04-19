"""Tools to be run on maya startup."""

import time

from maya import cmds

from psyhive import icons, refresh
from psyhive.utils import dprint, TMP, touch
from maya_psyhive import ui
from maya_psyhive.tools import fkik_switcher


def _touch_path_in_tmp():
    """Touch path in tmp dir."""
    _path = '{}/log/launch_{}.log'.format(TMP, time.strftime('%H%M%S'))
    dprint('TOUCH', _path)
    touch(_path)


def user_setup():
    """User setup."""

    dprint('PSYHIVE USER SETUP')

    _menu = ui.obtain_menu('psyhive', replace=True)

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
