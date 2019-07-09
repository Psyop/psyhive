"""Tools for installing a def into a py_gui inteface."""

import functools
import pprint

from psyhive.utils import lprint, to_nice

_RECORD_DATA = False
_DEFS = {}
_SECTIONS = []
_HIDDEN = []
_SECTION = None


class ArgUpdater(object):
    """Container to allow arg default/choices to be updated interactively."""

    def __init__(
            self, get_default=None, get_choices=None, label='Update',
            width=50):
        """Constructor.

        Args:
            get_default (fn): function to get arg default value
            get_choices (fn): function to get arg choices
            label (str): label for update button
            width (int): update button width
        """
        self._get_default = get_default
        self._get_choices = get_choices
        self.label = label
        if not self.label and get_choices:
            self.label = to_nice(get_choices.__name__)
        if not self.label and get_default:
            self.label = to_nice(get_default.__name__)
        self.width = width

    def get_choices(self):
        """Get choices for this arg."""
        return self._get_choices() if self._get_choices else None

    def get_default(self):
        """Get default value for this arg."""
        return self._get_default() if self._get_default else None


def get_installed_data(py_file):
    """Read py_gui installation data associated with the given py file.

    Args:
        py_file (PyFile): python file to read
    """
    global _SECTION, _RECORD_DATA, _SECTIONS, _DEFS, _HIDDEN

    _mod = py_file.get_module()

    _DEFS = []
    _SECTIONS = {}
    _HIDDEN = []
    _SECTION = None
    _RECORD_DATA = True
    reload(_mod)
    _RECORD_DATA = False

    return _DEFS, _SECTIONS, _HIDDEN


def hide_from_gui(func):
    """Decoration which hides the decorated function from py_gui.

    (This only applies if the all_defs flag is used)

    Args:
        func (fn): function to hide

    Returns:
        (fn): decorated function
    """
    global _HIDDEN

    if _RECORD_DATA:
        _HIDDEN.append(func.__name__)

    return func


def install_gui(
        icon=None, choices=None, hide=None, label=None, label_width=None,
        col=None, update=None, disable_reload=False, catch_error_=True,
        verbose=0):
    """Build a decorator which installs a def into a py_gui inteface.

    Any decorated def will appear in the py_gui interface for that file.

    Args:
        icon (str): icon to display for this def
        choices (dict): option lists for any args
        hide (str list): list of args to hide
        label (str): override label for this def
        label_width (int): label width in pixels
        col (str): button colour
        update (dict): dict of ArgUpdater objects for any args that need
            to be updated on the fly
        disable_reload (bool): no reload when this def is executed
        catch_error_ (bool): apply error catch decorator
        verbose (int): print process data
    """

    def _install_gui_decorator(func):

        # Keep list of install gui functions
        if _RECORD_DATA:
            global _DEFS
            _opts = {
                'icon': icon,
                'choices': choices,
                'hide': hide,
                'label': label,
                'label_width': label_width,
                'col': col,
                'update': update,
                'disable_reload': disable_reload,
                'catch_error_': catch_error_,
                'section': _SECTION,
            }
            _DEFS.append((func, _opts))
            lprint(' - INSTALLING GUI', func.__name__, verbose=verbose)
            lprint(pprint.pformat(_opts), verbose=verbose)

        @functools.wraps(func)
        def _install_gui_func(*args, **kwargs):
            _func = func
            return _func(*args, **kwargs)

        return _install_gui_func

    return _install_gui_decorator


class _Section(object):
    """Represents an interface section.

    This is a folding container that allows all the subsequent defs to
    be hidden if required.
    """

    def __init__(self, label, collapse=True):
        """Constructor.

        Args:
            label (str): label for section
            collapse (bool): whether section is collapsed or open
        """
        self.label = label
        self.collapse = collapse

        if _RECORD_DATA:
            global _SECTIONS
            if self.label in _SECTIONS:
                raise RuntimeError('Multiple sections with name - {}'.format(
                    self.label))
            _SECTIONS[self.label] = self

    def __repr__(self):
        return '<{}:{}>'.format(
            type(self).__name__.strip('_'), self.label)


def set_section(label, collapse=True):
    """Set current section.

    Args:
        label (str): label for section
        collapse (bool): whether section is collapsed or open
    """
    global _SECTION
    _SECTION = _Section(label, collapse=collapse)
