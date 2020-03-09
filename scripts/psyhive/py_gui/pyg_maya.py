"""Tools for building a py_gui using maya.cmds interface tools."""

from maya import cmds

from psyhive import icons, qt, refresh
from psyhive.utils import (
    wrap_fn, copy_text, lprint, chain_fns, get_single, File, to_nice,
    abs_path)

from psyhive.py_gui import pyg_base, pyg_install

from maya_psyhive import ui


def get_selection_reader(type_, verbose=0):
    """Get updater to get node transform with shape matching given type.

    Args:
        type_ (str): shape type to match (eg. nurbsCurve)
        verbose (int): print process data

    Returns:
        (ArgUpdater): pygui arg updater
    """

    def _get_sel():
        _sel = []
        for _node in cmds.ls(selection=True):

            _type = cmds.objectType(_node)
            lprint('TESTING SEL NODE', _node, _type, verbose=verbose)

            if _type == 'transform' and type_ == 'mesh':
                _node = get_single(
                    cmds.listRelatives(shapes=True, type=type_), catch=True)
                lprint(' - MAPPED TO', _node, verbose=verbose)

            if _node:
                lprint(' - ACCEPTED NODE', _node, verbose=verbose)
                _sel.append(_node)

        return get_single(_sel, catch=True)

    return pyg_install.ArgUpdater(_get_sel, label='Get selected')


def _apply_browser_path(target, default, title="Select file",
                        mode='SingleFileExisting'):
    """Launch a browser dialog and apply the selected path to the given field.

    Args:
        target (str): field to apply path to
        default (str): default directory for browser
        title (str): title for browser
        mode (str): browser mode - SingleFileExisting/SingleDirExisting
    """
    _file_mode = {'SingleFileExisting': 1, 'SingleDirExisting': 3}[mode]
    _file = get_single(cmds.fileDialog2(
        fileMode=_file_mode,  # Single existing file
        caption=title, okCaption='Select',
        startingDirectory=default))
    cmds.textField(target, edit=True, text=_file)


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


class MayaPyGui(pyg_base.BasePyGui):
    """Pygui interface built using maya.cmds interface tools."""

    def init_ui(self, rebuild_fn=None, verbose=0):
        """Initiate ui.

        Args:
            rebuild_fn (func): override rebuild function
            verbose (int): print process data
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
            update=None, browser=None, verbose=0):
        """Add an arg to the interface.

        Args:
            arg (PyArg): arg to add
            default (any): default value for arg
            label (str): override arg label
            choices (dict): list of options to show in the interface
            label_width (int): label width in pixels
            update (ArgUpdater): updater for this arg
            browser (BrowserLauncher): allow this field to be populated
                with a browser dialog
            verbose (int): print process data
        """
        lprint('ADDING', arg, verbose=verbose)
        _label_width = label_width or self.label_width

        # Some args don't appear in interface
        if arg.type_ in [tuple]:
            return None, None

        if update:
            cmds.rowLayout(
                numberOfColumns=3,
                columnWidth=((1, _label_width), (2, 100), (3, update.width)),
                adjustableColumn3=2)
        elif browser:
            cmds.rowLayout(
                numberOfColumns=3,
                columnWidth=((1, _label_width), (2, 100), (3, 19)),
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
        elif browser:
            _icon = cmds.iconTextButton(
                image1=icons.OPEN, width=19, height=19,
                style='iconOnly', command=wrap_fn(
                    _apply_browser_path, mode=browser.mode, target=_field,
                    title=browser.title, default=browser.get_default_dir()))

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
        cmds.menuItem(
            'Reset settings', parent=_menu,
            image=icons.EMOJI.find('Shower'),
            command=wrap_fn(self.reset_settings, def_=def_))

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
        self.save_settings()

    def finalise_ui(self):
        """Finalise interface."""
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.showWindow(self.ui_name)

        # Make sure window is not offscreen
        for _attr in ('topEdge', 'leftEdge'):
            _val = cmds.window(self.ui_name, query=True, **{_attr: True})
            if _val < 0:
                cmds.window(self.ui_name, edit=True, **{_attr: 100})

        self._resize_to_fit_children()

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

    def reset_settings(self, def_=None):
        """Reset current settings to defaults.

        Args:
            def_ (PyDef): only reset this def
        """

        # Avoid super for reload
        pyg_base.BasePyGui.reset_settings(self, def_=def_)
        cmds.menuItem(
            self._save_on_close, edit=True, checkBox=True)

    def set_section(self, section, verbose=0):
        """Set current section (implemented in subclass).

        Args:
            section (_Section): section to apply
            verbose (int): print process data
        """
        _resize = wrap_fn(
            cmds.evalDeferred, self._resize_to_fit_children,
            lowestPriority=True)
        _frame = cmds.frameLayout(
            collapsable=True, label=section.label, collapse=section.collapse,
            parent=self.master,
            collapseCommand=_resize,
            expandCommand=_resize,
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

    def rebuild(self):
        """Rebuild this interface."""
        super(MayaPyGui, self).rebuild()
        self._resize_to_fit_children()

    def _resize_to_fit_children(self):
        """Resize interface to fit child elements."""
        cmds.refresh()
        _col_h = cmds.columnLayout(self.master, query=True, height=True)
        _height = min(_col_h+25, self._height)
        cmds.window(self.ui_name, edit=True, height=_height, width=self._width)


class MayaPyShelfButton(pyg_base.BasePyGui):
    """Manages representing a python file as a shelf button.

    Clicking the button launches a MayaPyGui of the py file. The defs
    are also avaliable as right-click options.
    """

    def __init__(self, mod, parent, image, label=None, command=None,
                 button=None):
        """Constructor.

        Args:
            mod (module): py module to build into button
            parent (str): parent shelf
            image (str): path to icon
            label (str): override interface label
            command (str): override button command
            button (str): add menuItem elements to this existing button
                rather than creating a new one
        """
        self._file = File(abs_path(mod.__file__.replace('.pyc', '.py')))
        self.label = label or getattr(
            mod, 'PYGUI_TITLE', to_nice(self._file.basename))
        self.image = image

        # Create shelf button
        _cmd = command or '\n'.join([
            'from {} import MayaPyGui'.format(__name__),
            '_path = "{}"'.format(self._file.path),
            '_title = "{}"'.format(self.label),
            'MayaPyGui(_path, all_defs=True, title=_title)'])
        if button:
            self.button = button
            cmds.shelfButton(self.button, edit=True, command=_cmd)
        else:
            self.button = '{}_{}_PyShelfButton'.format(
                parent, self._file.basename)
            ui.add_shelf_button(
                self.button, image=image, parent=parent, command=_cmd,
                annotation=self.label, force=True)

        super(MayaPyShelfButton, self).__init__(
            self._file.path, all_defs=True, mod=mod)

    def init_ui(self, rebuild_fn=None, verbose=1):
        """Not applicable.

        Args:
            rebuild_fn (func): override rebuild function
            verbose (int): print process data
        """

        # Add label
        cmds.menuItem(
            '[{}]'.format(self.label), enable=False, image=self.image)

        # Open code option
        _cmd = '\n'.join([
            'from psyhive.utils import PyFile',
            '_file = "{}"'.format(self._file.path),
            'PyFile(_file).edit()'])
        cmds.menuItem('Open {} code'.format(self._file.basename),
                      command=_cmd, image=icons.EDIT)
        cmds.menuItem(divider=True)

    def add_arg(self, *args, **kwargs):
        """Not applicable.

        Args:
            arg (PyArg): arg to add
            default (any): default value for arg
            label (str): override arg label
            choices (dict): list of options to show in the interface
            label_width (int): label width in pixels
            update (ArgUpdater): updater for this arg
            browser (BrowserLauncher): add launch browser button
            verbose (int): print process data
        """
        return None, None

    def add_execute(self, def_, exec_fn, code_fn, help_fn, depth=35,
                    icon=None, label=None, col=None):
        """Add context option for the given def.

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
        cmds.menuItem(label, command=exec_fn, image=icon)

    def load_settings(self, verbose=0):
        """Not applicable.

        Args:
            verbose (int): print process data
        """

    def save_settings(self, verbose=0):
        """Not applicable.

        Args:
            verbose (int): print process data
        """

    def set_section(self, section, verbose=0):
        """Set section.

        Sections are applied as labelled dividers.

        Args:
            section (_Section): section to apply
            verbose (int): print process data
        """
        cmds.menuItem(divider=True, label=section.label)
