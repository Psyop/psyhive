"""Tools for managing the base class of any py_gui interface."""

import ast
import copy
import os
import pprint
import sys

import six

from psyhive import qt, icons
from psyhive.utils import (
    PyFile, to_nice, last, get_single, lprint, abs_path, write_yaml,
    read_yaml, dprint, Collection, str_to_seed, PyDef, PyBase,
    wrap_fn)
from psyhive.py_gui import install
from psyhive.py_gui.misc import (
    NICE_COLS, get_def_icon, get_exec_fn, get_help_fn, get_code_fn)

_EMPTY_SETTINGS = {
    'def': {}, 'section': {}, 'window': {"Geometry": {}}}


class BasePyGui(object):
    """Base class for any py_gui interface."""

    def __init__(
            self, path, title=None, all_defs=False, base_col=None, verbose=0):
        """Constructor.

        Args:
            path (str): path to build interface from
            title (str): override gui title
            all_defs (bool): force all defs into interface (by default
                only defs decorated with the py_gui.install decorator
                are added)
            base_col (QColor|str): override base colour for this interface
            verbose (int): print process data
        """

        # Store kwargs for rebuild
        self._kwargs = copy.copy(locals())
        self._kwargs.pop('self')

        self.py_file = PyFile(path)
        self.label_width = 70
        self._height = 400
        self.all_defs = all_defs
        self.section = None

        _mod = self.py_file.get_module(verbose=1)

        self.mod_name = _mod.__name__
        self.title = title or self.mod_name
        self.ui_name = self.mod_name.replace(".", "_")+"_ui"
        self.settings_file = abs_path(
            '{}/Psyop/settings/py_gui/{}.yml'.format(
                os.environ['HOME'], self.mod_name.replace('.', '_')))

        # Read attrs from module
        self.icon_set = getattr(_mod, 'PYGUI_ICON_SET', icons.FRUIT)
        self._width = getattr(_mod, 'PYGUI_WIDTH', 300)
        self.base_col = base_col or getattr(
            _mod, 'PYGUI_COL', str_to_seed(self.mod_name).choice(NICE_COLS))
        self.section_col = qt.HColor(self.base_col).blacken(0.5)
        assert isinstance(self.icon_set, Collection)

        # Build defs into ui
        self.read_settings_fns = copy.deepcopy(_EMPTY_SETTINGS)
        self.set_settings_fns = copy.deepcopy(_EMPTY_SETTINGS)
        _defs_data = self._get_defs_data()
        self.init_ui()
        lprint(
            'FOUND {:d} DEFS TO ADD'.format(len(_defs_data)), verbose=verbose)
        for _last, (_fn, _opts) in last(_defs_data):
            _def = self.py_file.find_def(_fn.__name__, catch=True)
            if _def:
                self.add_def(_def, opts=_opts, last_=_last)
        self.finalise_ui()
        if os.path.exists(self.settings_file):
            self.load_settings()

    def init_ui(self, rebuild_fn=None):
        """Initiate ui.

        Args:
            rebuild_fn (func): override rebuild function
        """
        dprint('Building ui {} ({})'.format(self.ui_name, self.base_col))

        # Add menu bar
        _interface = self.add_menu('Interface')
        self.add_menu_item(
            _interface, label='Rebuild', image=icons.EMOJI.find('Hammer'),
            command=rebuild_fn or self.rebuild)
        _settings = self.add_menu('Settings')
        self.add_menu_item(
            _settings, label='Save', image=icons.EMOJI.find('Floppy disk'),
            command=self.save_settings)
        self.add_menu_item(
            _settings, label='Reset', image=icons.EMOJI.find('Shower'),
            command=wrap_fn(self.reset_settings))  # Wrap to discard args
        self._save_on_close = self.add_menu_item(
            _settings, label='Save on close', checkbox=False)

    def add_menu(self, name):
        """Add menu to interface.

        Args:
            name (str): menu name
        """
        raise NotImplementedError

    def add_menu_item(self, parent, label, command=None, image=None,
                      checkbox=None):
        """Add menu item to interface.

        Args:
            parent (any): parent menu
            label (str): label for menu item
            command (func): item command
            image (str): path to item image
            checkbox (bool): item as checkbox (with this state)
        """
        raise NotImplementedError

    def add_arg(self, arg, default, label=None, choices=None, label_width=None,
                update=None, verbose=0):
        """Add an arg to the interface.

        Args:
            arg (PyArg): arg to add
            default (any): default value for arg
            label (str): override arg label
            choices (dict): list of options to show in the interface
            label_width (int): label width in pixels
            update (ArgUpdater): updater for this arg
            verbose (int): print process data
        """
        raise NotImplementedError

    def add_def(self, def_, opts, last_, verbose=0):
        """Add a def to the interface.

        The opts dict will be empty in the case of adding all defs
        (ie. not using the install_gui decorator) - so the defaults
        here need to be applied.

        Args:
            def_ (PyDef): def to add
            opts (dict): display options
            last_ (bool): whether this is last def in interface
            verbose (int): print process data
        """
        _update = opts.get('update') or {}
        _choices = opts.get('choices') or {}
        _hide = opts.get('hide') or []
        _disable_reload = opts.get('disable_reload') or False
        _section = opts.get('section')
        _catch_error = opts.get('catch_error_', True)

        if _section:
            self._set_section(_section)

        self.read_settings_fns['def'][def_.name] = {}
        self.set_settings_fns['def'][def_.name] = {}

        # Add args
        for _arg in def_.find_args():

            if _hide == '*' or _arg.name in _hide:
                continue
            lprint('  ADDING ARG', _arg, verbose=verbose)

            # Check for update fn
            _default = _arg.default
            _arg_choices = _choices.get(_arg.name)
            _arg_update = _update.get(_arg.name)
            if _arg_update and not isinstance(_arg_update, install.ArgUpdater):
                # Convert function to updater
                _arg_update = install.ArgUpdater(get_choices=_arg_update)
            if _arg_update:
                _arg_choices = _arg_update.get_choices() or _arg_choices
                _default = _arg_update.get_default() or _default

            _read_fn, _set_fn = self.add_arg(
                _arg,
                default=_default,
                label=to_nice(_arg.name),
                choices=_arg_choices,
                label_width=opts.get('label_width') or self.label_width,
                update=_arg_update)
            self.read_settings_fns['def'][def_.name][_arg.name] = _read_fn
            self.set_settings_fns['def'][def_.name][_arg.name] = _set_fn

        # Add execute
        _icon = opts.get('icon') or get_def_icon(
            def_.name, set_=self.icon_set)
        _label = opts.get('label') or to_nice(def_.name)
        _col = opts.get('col') or self.base_col
        _exec_fn = get_exec_fn(
            def_=def_, read_arg_fns=self.read_settings_fns['def'][def_.name],
            disable_reload=_disable_reload, catch_error_=True)
        _help_fn = get_help_fn(def_)
        _code_fn = get_code_fn(def_)
        self.add_execute(
            def_=def_, exec_fn=_exec_fn, help_fn=_help_fn, icon=_icon,
            label=_label, col=_col, code_fn=_code_fn)

        if not last_:
            self.add_separator()

    def add_execute(self, def_, exec_fn, code_fn, help_fn, depth=35,
                    icon=None, label=None, col=None):
        """Add execute button for the given def.

        Args:
            def_ (PyDef): def being added
            exec_fn (fn): function to call on execute
            code_fn (fn): function to call on jump to code
            help_fn (fn): function to call on launch help
            depth (int): size in pixels of def
            icon (str): path to icon to display
            label (str): override label from exec button
            col (str): colour for button
        """

    def add_separator(self):
        """Add a separator to the inteface."""

    def finalise_ui(self):
        """Finalise ui (implemented in subclass)."""

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
        _defs_data, _sections, _hidden = install.get_installed_data(
            self.py_file)
        _mod = self.py_file.get_module()

        if not self.all_defs:
            return _defs_data

        return _read_all_defs(
            py_file=self.py_file, mod=_mod, defs_data=_defs_data,
            sections=_sections, hidden=_hidden)

    def load_settings(self, verbose=0):
        """Load settings from disk.

        Args:
            verbose (int): print process data
        """
        _settings = read_yaml(self.settings_file)
        lprint('LOADING', _settings, verbose=verbose)
        for _attr, _attr_settings in _settings.items():
            print 'APPLING', _attr
            for _name, _settings in _attr_settings.items():
                lprint(' - NAME', _name, verbose=verbose)
                for _arg_name, _val in _settings.items():

                    # Find set fn
                    _set_fns = self.set_settings_fns
                    try:
                        _set_fn = _set_fns[_attr][_name][_arg_name]
                    except KeyError:
                        _set_fn = None

                    # Apply value
                    _applied = False
                    if _set_fn:
                        lprint(
                            '   - APPLYING', _arg_name, _val, _set_fn,
                            verbose=verbose)
                        try:
                            _set_fn(_val)
                        except TypeError:
                            continue
                        else:
                            _applied = True
                    if not _applied:
                        lprint('   - FAILED TO APPLY', _arg_name, _val)

        dprint('Loaded settings', self.settings_file)

    def _read_settings(self, verbose=0):
        """Read current settings from interface.

        Args:
            verbose (int): print process data

        Returns:
            (dict): current settings
        """
        _settings = copy.deepcopy(_EMPTY_SETTINGS)
        for _attr in ['def', 'section', 'window']:
            _items = self.read_settings_fns[_attr].items()
            lprint('READING', _attr, _items, verbose=verbose)
            for _name, _read_settings_fns in _items:
                lprint(' - READING', _name, _read_settings_fns,
                       verbose=verbose)
                _settings[_attr][_name] = {}
                for _arg, _arg_fn in _read_settings_fns.items():
                    _val = _arg_fn()
                    if isinstance(_val, six.string_types):
                        _val = str(_val)
                    _settings[_attr][_name][_arg] = _val
        return _settings

    def rebuild(self):
        """Rebuild this interface."""
        _class_name = self.__class__.__name__
        _mod_name = self.__class__.__module__
        _class = getattr(sys.modules[_mod_name], _class_name)
        _class(**self._kwargs)

    def reset_settings(self, def_=None):
        """Reset current settings to defaults.

        Args:
            def_ (PyDef): only reset this def
        """
        print 'RESETTING SETTINGS'
        _sections = set()
        for _fn, _data in self._get_defs_data():
            _py_def = self.py_file.find_def(_fn.__name__)
            if def_ and not def_ == _py_def:
                continue
            print' - ADDING', _fn, _data
            for _py_arg in _py_def.find_args():
                print '   - SETTING', _py_arg, _py_arg.default
                _set_fn = self.set_settings_fns[
                    'def'][_py_def.name][_py_arg.name]
                _set_fn(_py_arg.default)
            _section = _data.get('section')
            if _section:
                print ' - SECTION', _section
                _sections.add(_section)

        if not def_:
            print 'SECTIONS', _sections
            for _section in _sections:
                print ' - ADDING', _section, _section.collapse
                _set_fn = self.set_settings_fns[
                    'section'][_section.label]['collapse']
                _set_fn(_section.collapse)

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

    def _set_section(self, section, verbose=0):
        """Set current section (implemented in subclass).

        Args:
            section (_Section): section to apply
            verbose (int): print process data
        """


def _read_all_defs(py_file, mod, defs_data, sections, hidden, verbose=1):
    """Read all defs data from the given file.

    This is complicated as any information installed to defs needs to
    still be applied, but any section information needs to also be
    applied to defs which haven't been installed.

    The PyFile subclass is used which matches section objects and
    combines this with the def information as it read the ast.

    Args:
        py_file (PyFile): file to read defs from
        mod (module): module from this py file
        defs_data (list): installed py_gui def data (def/opts)
        sections (dict): installed section data (label/section)
        hidden (str list): list of functions to hide
        verbose (int): print process data

    Returns:
        (dict): defs data (list of def/opts data)
    """

    class _AstSectionMatcher(PyBase):
        """Represents a py_gui section."""

        def __init__(self, expr_, py_file):
            super(_AstSectionMatcher, self).__init__(
                expr_, py_file=py_file, name='SectionExpr', read_docs=False)
            if (
                    not isinstance(expr_, ast.Expr) or
                    not hasattr(expr_.value, 'func') or
                    not expr_.value.func.attr == 'set_section' or
                    not expr_.value.func.value.id == 'py_gui'):
                raise ValueError
            self.label = expr_.value.args[0].s

        def __repr__(self):
            return '<{}:{}>'.format(
                type(self).__name__.strip('_'), self.label)

    class _PyFileParser(PyFile):
        """PyFile subclass that finds py_gui sections within the py code."""

        def _read_child(self, ast_item, verbose=0):
            _obj = super(_PyFileParser, self)._read_child(ast_item)
            if not _obj:
                try:
                    _obj = _AstSectionMatcher(ast_item, py_file=self)
                except ValueError:
                    pass
            return _obj

    # Read file to get defs ordering
    # The section data is managed internally - section data from the
    # install is ignored
    lprint("READING ALL DEFS", verbose=verbose)
    _section = None
    _data = []
    for _child in _PyFileParser(py_file.path).find_children():

        # Add def
        if isinstance(_child, PyDef):
            if _child.is_private or _child.clean_name in hidden:
                continue
            _defs_data = get_single([
                (_in_def, _in_opts) for _in_def, _in_opts in defs_data
                if _in_def.__name__ == _child.name], catch=True)
            if not _defs_data:
                _def = getattr(mod, _child.name)
                _defs_data = _def, {'section': _section}
            _defs_data[1]['section'] = _section
            _data.append(_defs_data)
            _section = None

        # Add section
        elif isinstance(_child, _AstSectionMatcher):
            print " - SECTION", _child, sections
            _section = sections[_child.label]

    return _data
