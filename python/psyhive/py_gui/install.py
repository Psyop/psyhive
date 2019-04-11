"""Tools for installing a def into a py_gui inteface."""

import functools

from psyhive.utils import lprint

INSTALL_GUI_DEFS = {}


def install_gui(
        icon=None, choices=None, hide=None, section=None,
        label=None, label_width=None, col=None, verbose=False):
    """Build a decorator which installs a def into a py_gui inteface.

    Any decorated def will appear in the py_gui interface for that file.

    Args:
        icon (str): icon to display for this def
        choices (dict): option lists for any args
        hide (str list): list of args to hide
        section (Section): assign this def to a section of the interface
        label (str): override label for this def
        label_width (int): label width in pixels
        col (str): button colour
        verbose (int): print process data
    """

    def _install_gui_decorator(func):

        global INSTALL_GUI_DEFS

        # Keep list of install gui functions
        _opts = {
            'icon': icon,
            'choices': choices,
            'hide': hide,
            'section': section,
            'label': label,
            'label_width': label_width,
            'col': col,
        }
        if func.__module__ not in INSTALL_GUI_DEFS:
            INSTALL_GUI_DEFS[func.__module__] = []
        INSTALL_GUI_DEFS[func.__module__].append((func, _opts))
        lprint(' - INSTALLING GUI', func, INSTALL_GUI_DEFS, verbose=verbose)

        @functools.wraps(func)
        def _install_gui_func(*args, **kwargs):
            _func = func
            return _func(*args, **kwargs)

        return _install_gui_func

    return _install_gui_decorator


def get_installed_data(py_file):
    """Read py_gui installation data associated with the given py file.

    Args:
        py_file (PyFile): python file to read
    """
    _mod = py_file.get_module()
    INSTALL_GUI_DEFS[_mod.__name__] = []
    reload(_mod)
    return INSTALL_GUI_DEFS[_mod.__name__]


class Section(object):
    """Used to represent a section of the interface."""

    def __init__(self, name):
        """Constructor.

        Args:
            name (str): section name
        """
        self.name = name
