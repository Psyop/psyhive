"""Tools for building a py_gui using maya.cmds interface tools."""

import os

from maya import cmds

from psyhive import icons, qt, refresh
from psyhive.utils import wrap_fn, copy_text, lprint, chain_fns, get_single

from psyhive.py_gui import base, install

from maya_psyhive import ui


def get_selection_reader(type_):
    """Get updater to get node transform with shape matching given type.

    Args:
        type_ (str): shape type to match (eg. nurbsCurve)

    Returns:
        (ArgUpdater): pygui arg updater
    """

    def _get_sel():
        _sel = []
        for _node in cmds.ls(selection=True):
            _shp = get_single(
                cmds.listRelatives(shapes=True, type=type_), catch=True)
            if _shp:
                _sel.append(_node)
        return get_single(_sel, catch=True)

    return install.ArgUpdater(_get_sel, label='Get selected')


def _get_update_fn(set_fn, update, field):
    """Get function to execute when arg field needs updating.

    Args:
        set_fn (fn): function to set arg field
        update (ArgUpdater): updater object
        field (str): field being updated
    """

    def _update_fn(*xargs):
        del xargs
        _choices = update.get_choices()
        _default = update.get_default()
        if _choices:
            ui.populate_option_menu(field, _choices)
            ui.set_option_menu(field, _default)
            print 'UPDATED CHOICES', _default, _choices
        else:
            print 'UPDATED', _default
            set_fn(_default)

    return _update_fn


class MayaPyGui(base.BasePyGui):
    """Pygui interface built using maya.cmds interface tools."""

    def init_ui(self, rebuild_fn=None):
        """Initiate ui.

        Args:
            rebuild_fn (func): override rebuild function
        """

        # Init window
        if cmds.window(self.ui_name, exists=True):
            cmds.deleteUI(self.ui_name)
        cmds.window(
            self.ui_name, title=self.title, width=400, menuBar=True,
            closeCommand=self.close_event)

        _rebuild_fn = rebuild_fn or wrap_fn(cmds.evalDeferred, self.rebuild)
        super(MayaPyGui, self).init_ui(rebuild_fn=_rebuild_fn)

        # Build layouts
        self.scroll = self.ui_name+'_scroll'
        cmds.scrollLayout(self.scroll, childResizable=1)
        self.master = self.ui_name+'_master'
        cmds.columnLayout(self.master, adjustableColumn=1)

        # Setup set window settings fns
        for _attr in ['width', 'height']:
            _set_fn = wrap_fn(
                cmds.window, self.ui_name, edit=True, arg_to_kwarg=_attr)
            self.set_settings_fns['window']['Geometry'][_attr] = _set_fn
            _read_fn = wrap_fn(
                cmds.window, self.ui_name, query=True, **{_attr: True})
            self.read_settings_fns['window']['Geometry'][_attr] = _read_fn

    def add_arg(
            self, arg, default, label=None, choices=None, label_width=None,
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
        lprint('ADDING', arg, verbose=verbose)
        _label_width = label_width or self.label_width

        if update:
            cmds.rowLayout(
                numberOfColumns=3,
                columnWidth=((1, _label_width), (2, 100), (3, update.width)),
                adjustableColumn3=2)
        else:
            cmds.rowLayout(
                numberOfColumns=2,
                columnWidth=((1, _label_width), (2, 1000)),
                adjustableColumn2=2)

        cmds.text(label or arg.name, align='left')

        _set_fn = None
        if choices:
            _field = cmds.optionMenu()
            ui.populate_option_menu(_field, choices)
            _read_fn = wrap_fn(ui.read_option_menu, _field, type_=arg.type_)
            _set_fn = wrap_fn(ui.set_option_menu, _field, arg_to_kwarg='value')
            ui.set_option_menu(_field, default)
        elif arg.type_ is int:
            _field = cmds.intField(value=default)
            _read_fn = wrap_fn(cmds.intField, _field, query=True, value=True)
            _set_fn = wrap_fn(
                cmds.intField, _field, arg_to_kwarg='value', edit=True)
        elif arg.type_ is float:
            _field = cmds.floatField(value=default)
            _read_fn = wrap_fn(cmds.floatField, _field, query=True, value=True)
            _set_fn = wrap_fn(
                cmds.floatField, _field, arg_to_kwarg='value', edit=True)
        elif arg.type_ is str or arg.type_ is None:
            _field = cmds.textField(text=default or '')
            _read_fn = wrap_fn(cmds.textField, _field, query=True, text=True)
            _set_fn = wrap_fn(
                cmds.textField, _field, arg_to_kwarg='text', edit=True)
        elif arg.type_ is bool:
            _field = cmds.checkBox(label='', value=default)
            _read_fn = wrap_fn(cmds.checkBox, _field, query=True, value=True)
            _set_fn = wrap_fn(
                cmds.checkBox, _field, arg_to_kwarg='value', edit=True)
        else:
            raise ValueError(arg.type_)

        if update:
            cmds.button(
                label=update.label, height=19, command=_get_update_fn(
                    set_fn=_set_fn, update=update, field=_field))

        cmds.setParent('..')

        return _read_fn, _set_fn

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
        _help_icon = icons.EMOJI.find('Information')

        _btn_width = 10
        cmds.rowLayout(
            numberOfColumns=3,
            columnWidth3=(depth, _btn_width, depth),
            adjustableColumn=2,
            height=depth)
        _icon = cmds.iconTextButton(
            image1=icon, width=depth, height=depth,
            style='iconOnly', command=code_fn)
        _col = qt.get_col(col if col else self.base_col)
        _btn = cmds.button(
            label=label, height=depth, width=_btn_width, command=exec_fn,
            align='center', backgroundColor=_col.to_tuple(mode='float'))
        cmds.iconTextButton(
            image1=_help_icon, height=depth, width=depth,
            style='iconOnly', command=help_fn)
        cmds.setParent('..')

        # Add right-click options (exec button)
        _menu = cmds.popupMenu(parent=_btn)
        _cmd = '\n'.join([
            'import {} as _mod',
            'print _mod.{}',
        ]).format(self.py_file.get_module().__name__, def_.name)
        cmds.menuItem(
            'Copy import statement', parent=_menu,
            image=icons.COPY,
            command=wrap_fn(copy_text, _cmd))
        cmds.menuItem(
            'Lock button', parent=_menu,
            image=icons.EMOJI.find('Locked'),
            command=wrap_fn(cmds.button, _btn, edit=True, enable=False))
        cmds.menuItem(
            'Refresh and execute', parent=_menu,
            image=icons.REFRESH,
            command=chain_fns(refresh.reload_libs, exec_fn))

        # Add right-click options (code icon)
        _menu = cmds.popupMenu(parent=_icon)
        cmds.menuItem(
            'Unlock button', parent=_menu,
            image=icons.EMOJI.find('Unlocked'),
            command=wrap_fn(cmds.button, _btn, edit=True, enable=True))

    def add_separator(self):
        """Add separator."""
        cmds.separator(style='out', height=10, horizontal=True)

    def add_menu(self, name):
        """Add menu to interface.

        Args:
            name (str): menu name
        """
        return cmds.menu(label=name)

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
        _kwargs = {}
        if image:
            _kwargs['image'] = image
        if command:
            _kwargs['command'] = command
        if checkbox is not None:
            _kwargs['checkBox'] = checkbox
        return cmds.menuItem(parent=parent, label=label, **_kwargs)

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
            height=min(_col_h+27, self._height),
            width=self._width)

    def close(self):
        """Close this window."""
        if cmds.window(self.ui_name, exists=True):
            cmds.deleteUI(self.ui_name)

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
            self._save_on_close, edit=True, checkBox=True)

    def _set_section(self, section, verbose=0):
        """Set current section (implemented in subclass).

        Args:
            section (_Section): section to apply
            verbose (int): print process data
        """
        _frame = cmds.frameLayout(
            collapsable=True, label=section.label, collapse=section.collapse,
            parent=self.master,
            backgroundColor=self.section_col.to_tuple(mode='float'),
        )
        cmds.columnLayout(parent=_frame, adjustableColumn=1)
        cmds.separator(style='none', height=1, horizontal=True)

        self.read_settings_fns['section'][section.label] = {}
        self.read_settings_fns['section'][section.label]['collapse'] = wrap_fn(
            cmds.frameLayout, _frame, query=True, collapse=True)

        self.set_settings_fns['section'][section.label] = {}
        self.set_settings_fns['section'][section.label]['collapse'] = wrap_fn(
            cmds.frameLayout, _frame, edit=True, arg_to_kwarg='collapse')

        lprint(
            '[py_gui.maya] SETTING SECTION', section, section.collapse,
            verbose=verbose)
