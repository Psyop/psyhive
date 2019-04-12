"""Tools to be run on maya startup."""

import time

from psyhive.utils import dprint, TMP, touch


def user_setup():
    """User setup."""
    dprint('USER SETUP')
    _path = '{}/log/launch_{}.log'.format(TMP, time.strftime('%H%M%S'))
    dprint('TOUCH', _path)
    touch(_path)

