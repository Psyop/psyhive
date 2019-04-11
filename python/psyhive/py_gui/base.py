"""Tools for managing the base class of any py_gui interface."""

import copy
import os
import pprint
import sys

from psyhive import icons
from psyhive.utils import (
    PyFile, to_nice, last, get_single, lprint, abs_path, write_yaml,
    read_yaml, dprint, Collection)
from psyhive.py_gui import install


class BasePyGui(object):
    """Base class for any py_gui interface."""

    def __init__(self, path, title=None, all_defs=False):
        """Constructor.

        Args:
            path (str): path to build interface from
            title (str): override gui title
            all_defs (bool): force all defs into interface (by default
                only defs decorated with the py_gui.install decorator
                are added)
        """

        # Store kwargs for rebuild
        self._kwargs = copy.copy(locals())
        self._kwargs.pop('self')

        self.py_file = PyFile(path)
        self.label_width = 70
        self.width = 300
        self.height = 400
        self.all_defs = all_defs

        self.mod_name = self.py_file.get_module().__name__
        self.title = title or self.mod_name
        self.ui_name = self.mod_name.replace(".", "_")+"_ui"
        self.settings_file = abs_path(
            '{}/Psyop/settings/py_gui/{}.yml'.format(
                os.environ['HOME'], self.mod_name.replace('.', '_')))

        self.icon_set = getattr(
            self.py_file.get_module(), 'ICON_SET', icons.FRUIT)
        assert isinstance(self.icon_set, Collection)

        # Build defs into ui
        self.read_arg_fns = {}
        self.set_arg_fns = {}
        _defs_data = self._get_defs_data()
        self.init_ui()
        for _last, (_fn, _opts) in last(_defs_data):
            _def = self.py_file.find_def(_fn.__name__)
            self.add_def(_def, opts=_opts, last_=_last)
        self.finalise_ui()
        if os.path.exists(self.settings_file):
            self.load_settings()

    def add_arg(
            self, arg, name=None, choices=None, label_width=None,
            verbose=0):
        """Add an arg to the interface.

        Args:
            arg (PyArg): arg to add
            name (str): override arg name
            choices (dict): list of options to show in the interface
            label_width (int): label width in pixels
            verbose (int): print process data
        """

    def add_def(self, def_, opts, last_, verbose=0):
        """Add a def to the interface.

        Args:
            def_ (PyDef): def to add
            opts (dict): display options
            last_ (bool): whether this is last def in interface
            verbose (int): print process data
        """
        _choices = opts.get('choices') or {}
        _hide = opts.get('hide') or []

        self.read_arg_fns[def_.name] = {}
        self.set_arg_fns[def_.name] = {}

        # Add args
        for _arg in def_.find_args():
            if _arg.name in _hide:
                continue
            lprint('  ADDING ARG', _arg, verbose=verbose)
            self.add_arg(
                _arg,
                name=to_nice(_arg.name),
                choices=_choices.get(_arg.name),
                label_width=opts.get('label_width'),
            )

        self.add_execute(
            def_=def_,
            icon=opts.get('icons'),
            label=opts.get('label'),
            col=opts.get('col'),
        )

    def add_execute(self, def_, depth=35, icon=None, label=None, col=None):
        """Add execute button for the given def.

        Args:
            def_ (PyDef): def being added
            depth (int): size in pixels of def
            icon (str): path to icon to display
            label (str): override label from exec button
            col (str): colour for this button
        """

    def close_event(self, verbose=0):
        """Executed on close.

        Args:
            verbose (int): print process data
        """
        print 'CLOSING', self

    def _get_defs_data(self):
        """Get list of defs to add to interface.

        Returns:
            (fn/opts list): list of functions and options
        """

        # Get list of defs to add
        _installed_data = install.get_installed_data(self.py_file)
        _mod = self.py_file.get_module()

        if not self.all_defs:
            return _installed_data

        # Read file to get defs ordering
        _data = []
        for _py_def in self.py_file.find_defs():
            if _py_def.is_private:
                continue
            _def_data = get_single([
                (_in_def, _in_opts) for _in_def, _in_opts in _installed_data
                if _in_def.__name__ == _py_def.name], catch=True)
            if not _def_data:
                _def = getattr(_mod, _py_def.name)
                _def_data = _def, {}
            _data.append(_def_data)

        return _data

    def finalise_ui(self):
        """Finalise ui (implemented in subclass)."""

    def init_ui(self):
        """Initiate ui (implemented in subclass)."""

    def load_settings(self, verbose=0):
        """Load settings from disk.

        Args:
            verbose (int): print process data
        """
        _settings = read_yaml(self.settings_file)
        lprint('LOADING', _settings, verbose=verbose)
        for _def_name, _arg_settings in _settings.items():
            lprint('DEF NAME', _def_name, verbose=verbose)
            for _arg_name, _val in _arg_settings.items():
                _set_fn = self.set_arg_fns[_def_name][_arg_name]
                if _set_fn:
                    lprint(
                        ' - APPLYING', _arg_name, _val, _set_fn,
                        verbose=verbose)
                    _set_fn(_val)
                else:
                    lprint(
                        ' - FAILED TO APPLY', _arg_name, _val)

        dprint('Loaded settings', self.settings_file)

    def _read_settings(self):
        """Read current settings from interface.

        Returns:
            (dict): current settings
        """
        _settings = {}
        for _def, _read_arg_fns in self.read_arg_fns.items():
            if not _read_arg_fns:
                continue
            _settings[_def] = {}
            for _arg, _arg_fn in _read_arg_fns.items():
                _val = _arg_fn()
                _settings[_def][_arg] = _val

        return _settings

    def rebuild(self):
        """Rebuild this interface."""
        _class_name = self.__class__.__name__
        _mod_name = self.__class__.__module__
        _class = getattr(sys.modules[_mod_name], _class_name)
        _class(**self._kwargs)

    def reset_settings(self):
        """Reset current settings to defaults."""
        print 'RESETTING SETTINGS'
        for _fn, _ in self._get_defs_data():
            _py_def = self.py_file.find_def(_fn.__name__)
            print _fn
            for _py_arg in _py_def.find_args():
                print ' - SETTING', _py_arg, _py_arg.default
                _set_fn = self.set_arg_fns[_py_def.name][_py_arg.name]
                _set_fn(_py_arg.default)

    def save_settings(self, verbose=1):
        """Save current settings to disk.

        Args:
            verbose (int): print process data
        """
        _settings = self._read_settings()
        if verbose > 1:
            pprint.pprint(_settings)
        dprint('Saved settings', self.settings_file, verbose=verbose)
        write_yaml(file_=self.settings_file, data=_settings)
