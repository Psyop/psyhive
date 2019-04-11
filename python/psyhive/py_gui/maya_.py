"""Tools for building a py_gui using maya.cmds interface tools."""

import os

from maya import cmds

from psyhive import icons, qt
from psyhive.utils import wrap_fn, to_nice, copy_text, lprint, dprint

from psyhive.py_gui import base
from psyhive.py_gui.misc import (
    get_code_fn, get_exec_fn, get_help_fn, get_def_icon)


def _read_option_menu(name, type_):
    """Read the selected item in an option menu.

    Args:
        name (str): option menu to read
        type_ (type): type of result to obtain

    Returns:
        (any): selected item if given type
    """
    _sel = cmds.optionMenu(name, query=True, select=True)
    _items = cmds.optionMenu(name, query=True, itemListLong=True)
    _item = _items[_sel-1]
    _text = cmds.menuItem(_item, query=True, label=True)
    return type_(_text)


def _set_option_menu(name, value):
    """Set the selected item in an option menu.

    Args:
        name (str): option menu to update
        value (any): string value to apply
    """
    _items = [
        cmds.menuItem(_item, query=True, label=True)
        for _item in cmds.optionMenu(name, query=True, itemListLong=True)]
    if str(value) not in _items:
        print 'Failed to select', value, 'from', _items
        return
    _idx = _items.index(str(value))
    cmds.optionMenu(name, edit=True, select=_idx+1)


class MayaPyGui(base.BasePyGui):
    """Pygui interface built using maya.cmds interface tools."""

    def close(self):
        """Close this window."""
        if cmds.window(self.ui_name, exists=True):
            cmds.deleteUI(self.ui_name)

    def init_ui(self):
        """Initiate interface."""
        dprint('Building ui', self.ui_name)
        if cmds.window(self.ui_name, exists=True):
            cmds.deleteUI(self.ui_name)
        cmds.window(
            self.ui_name, title=self.title, width=400, menuBar=True,
            closeCommand=self.close_event)

        # Add menu bar
        cmds.menu(label='Interface')
        cmds.menuItem(
            label='Rebuild', image=icons.EMOJI.find('Hammer'),
            command=wrap_fn(cmds.evalDeferred, self.rebuild))
        cmds.menu(label='Settings')
        cmds.menuItem(
            label='Save', image=icons.EMOJI.find('Floppy disk'),
            command=self.save_settings)
        cmds.menuItem(
            label='Reset', image=icons.EMOJI.find('Shower'),
            command=wrap_fn(self.reset_settings))  # Wrap to discard args
        self._save_on_close = cmds.menuItem(
            label='Save on close', image=icons.EMOJI.find('Floppy disk'),
            checkBox=False)

        # Build layouts
        self.scroll = self.ui_name+'_scroll'
        cmds.scrollLayout(self.scroll, childResizable=1)
        self.master = self.ui_name+'_master'
        cmds.columnLayout(self.master, adjustableColumn=1)

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
        lprint('ADDING', arg, verbose=verbose)
        _label_width = label_width or self.label_width

        cmds.rowLayout(
            numberOfColumns=2,
            columnWidth=((1, _label_width), (2, 1000)),
            adjustableColumn2=2)

        cmds.text(name or arg.name, align='left')

        _set_fn = None
        if choices:
            _menu = cmds.optionMenu()
            for _choice in choices:
                cmds.menuItem(label=_choice, parent=_menu)
            _read_fn = wrap_fn(_read_option_menu, _menu, type_=arg.type_)
            _set_fn = wrap_fn(_set_option_menu, _menu, arg_to_kwarg='value')
            _set_option_menu(_menu, arg.default)
        elif arg.type_ is int:
            _field = cmds.intField(value=arg.default)
            _read_fn = wrap_fn(cmds.intField, _field, query=True, value=True)
            _set_fn = wrap_fn(
                cmds.intField, _field, arg_to_kwarg='value', edit=True)
        elif arg.type_ is float:
            _field = cmds.floatField(value=arg.default)
            _read_fn = wrap_fn(cmds.floatField, _field, query=True, value=True)
            _set_fn = wrap_fn(
                cmds.floatField, _field, arg_to_kwarg='value', edit=True)
        elif arg.type_ is str or arg.type_ is None:
            _field = cmds.textField(text=arg.default or '')
            _read_fn = wrap_fn(cmds.textField, _field, query=True, text=True)
            _set_fn = wrap_fn(
                cmds.textField, _field, arg_to_kwarg='text', edit=True)
        elif arg.type_ is bool:
            _field = cmds.checkBox(label='', value=arg.default)
            _read_fn = wrap_fn(cmds.checkBox, _field, query=True, value=True)
            _set_fn = wrap_fn(
                cmds.checkBox, _field, arg_to_kwarg='value', edit=True)
        else:
            raise ValueError(arg.type_)

        self.read_arg_fns[arg.def_.name][arg.name] = _read_fn
        self.set_arg_fns[arg.def_.name][arg.name] = _set_fn

        cmds.setParent('..')

    def add_def(self, def_, opts, last_, verbose=0):
        """Add a def to the interface.

        Args:
            def_ (PyDef): def to add
            opts (dict): display options
            last_ (bool): whether this is last def in interface
            verbose (int): print process data
        """
        _kwargs = locals()
        _kwargs.pop('self')
        super(MayaPyGui, self).add_def(**_kwargs)
        if not last_:
            cmds.separator(style='out', height=10, horizontal=True)

    def add_execute(self, def_, depth=35, icon=None, label=None, col=None):
        """Add execute button for the given def.

        Args:
            def_ (PyDef): def being added
            depth (int): size in pixels of def
            icon (str): path to icon to display
            label (str): override label from exec button
            col (str): colour for button
        """
        _icon = icon or get_def_icon(def_.name, set_=self.icon_set)
        _help_icon = icons.EMOJI.find('Information')
        _btn_width = 10
        cmds.rowLayout(
            numberOfColumns=3,
            columnWidth3=(depth, _btn_width, depth),
            adjustableColumn=2,
            height=depth)
        _icon = cmds.iconTextButton(
            image1=_icon, width=depth, height=depth,
            style='iconOnly', command=get_code_fn(def_))
        _col = qt.get_col(col) if col else qt.HColor('grey')
        _btn = cmds.button(
            label=label or to_nice(def_.name),
            height=depth,
            width=_btn_width,
            command=get_exec_fn(
                def_=def_, read_arg_fns=self.read_arg_fns[def_.name]),
            align='center', backgroundColor=_col.to_tuple(mode='float'))
        cmds.iconTextButton(
            image1=_help_icon, height=depth, width=depth,
            style='iconOnly', command=get_help_fn(def_))
        cmds.setParent('..')

        # Add right-click options (exec button)
        _menu = cmds.popupMenu(parent=_btn)
        _cmd = '\n'.join([
            'import {} as _mod',
            'print _mod.{}',
        ]).format(self.py_file.get_module().__name__, def_.name)
        cmds.menuItem(
            'Copy import statement', parent=_menu,
            image=icons.EMOJI.find('Copy'),
            command=wrap_fn(copy_text, _cmd))
        cmds.menuItem(
            'Lock button', parent=_menu,
            image=icons.EMOJI.find('Locked'),
            command=wrap_fn(cmds.button, _btn, edit=True, enable=False))

        # Add right-click options (code icon)
        _menu = cmds.popupMenu(parent=_icon)
        cmds.menuItem(
            'Unlock button', parent=_menu,
            image=icons.EMOJI.find('Unlocked'),
            command=wrap_fn(cmds.button, _btn, edit=True, enable=True))

    def close_event(self, verbose=0):
        """Executed on close.

        Args:
            verbose (int): print process data
        """

        # Save settings if required
        _save_on_close = cmds.menuItem(
            self._save_on_close, query=True, checkBox=True)
        lprint(
            'CLOSING {} save_on_close={:d}'.format(self, _save_on_close),
            verbose=verbose)
        if _save_on_close:
            self.save_settings()
        elif os.path.exists(self.settings_file):
            print 'REMOVING SETTINGS FILE', self.settings_file
            os.remove(self.settings_file)

    def finalise_ui(self):
        """Finalise interface."""
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.showWindow(self.ui_name)
        _col_h = cmds.columnLayout(self.master, query=True, height=True)
        cmds.window(
            self.ui_name, edit=True,
            height=min(_col_h+27, self.height),
            width=self.width)

    def load_settings(self, verbose=0):
        """Load settings from disk.

        Args:
            verbose (int): print process data
        """
        super(MayaPyGui, self).load_settings()
        cmds.menuItem(
            self._save_on_close, edit=True, checkBox=True)

    def reset_settings(self):
        """Reset settings to defaults."""
        base.BasePyGui.reset_settings(self)  # Avoid super for reload
        cmds.menuItem(
            self._save_on_close, edit=True, checkBox=False)
