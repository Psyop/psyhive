"""Tools relating to dev mode toggle."""

import functools
import os

from .misc import lprint


def dev_mode(verbose=0):
    """Test whether dev mode env var is set.

    Args:
        verbose (int): print process data

    Returns:
        (bool): whether we are in dev mode
    """
    _dev = os.environ.get('PSYHIVE_DEV')
    lprint('PSYHIVE_DEV', _dev, bool(_dev), verbose=verbose)
    return bool(_dev)


def revert_dev_mode(func):
    """Decorator which reverts any changes to dev mode.

    Args:
        func (fn): function to decorate

    Returns:
        (dec): decorator
    """

    @functools.wraps(func)
    def _dev_mode_revert_func(*args, **kwargs):

        _dev_mode = dev_mode()
        _result = func(*args, **kwargs)
        if not _dev_mode:
            if 'PSYHIVE_DEV' in os.environ:
                del os.environ['PSYHIVE_DEV']
        else:
            os.environ['PSYHIVE_DEV'] = '1'
        assert dev_mode() == _dev_mode
        return _result

    return _dev_mode_revert_func


def set_dev_mode(value, verbose=0):
    """Set dev mode.

    Args:
        value (bool): dev mode setting
        verbose (int): print process data
    """
    if value:
        os.environ['PSYHIVE_DEV'] = '1'
    elif 'PSYHIVE_DEV' in os.environ:
        del os.environ['PSYHIVE_DEV']
    os.environ['PSYHIVE_ICONS_EMOJI'] = (
        'P:/global/code/pipeline/bootstrap/psycons/icon_packs/EMOJI/'
        'icon.%04d.png')
    lprint('PSYHIVE_DEV', dev_mode(), verbose=verbose)
