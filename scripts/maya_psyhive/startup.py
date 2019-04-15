"""Tools to be run on maya startup."""

import time

from maya import cmds

from psyhive import icons
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
        'import {fkik} as _mod',
        '_mod.launch_gui()',
    ]).format(fkik=fkik_switcher.__name__)
    cmds.menuItem(
        label='FK/IK switcher', command=_cmd,
        image=icons.EMOJI.find('Flexed Biceps: Light Skin Tone'))
