"""Tools to be run on maya startup."""

import logging

from maya import cmds

from psyhive import icons, refresh, qt, py_gui
from psyhive.tools import track_usage
from psyhive.utils import (
    dprint, wrap_fn, get_single, lprint, File, str_to_seed, PyFile,
    to_nice)

from maya_psyhive import ui, shows
from maya_psyhive.tools import fkik_switcher

from .psu_script_editor import script_editor_add_project_opts

_BUTTONS = {
    'IKFK': {
        'cmd': '\n'.join([
            'import {} as fkik_switcher'.format(fkik_switcher.__name__),
            'fkik_switcher.launch_interface()']),
        'label': 'FK/IK switcher',
        'image': fkik_switcher.ICON},
}


def _add_elements_to_psyop_menu(verbose=0):
    """Add elements to psyop menu.

    Args:
        verbose (int): print process data
    """
    dprint('ADDING {:d} TO PSYOP MENU'.format(len(_BUTTONS)), verbose=verbose)
    _menu = ui.obtain_menu('Psyop')

    _children = cmds.menu(_menu, query=True, itemArray=True) or []
    _anim = get_single(
        [
            _child for _child in _children
            if cmds.menuItem(_child, query=True, label=True) == 'Animation'],
        catch=True)

    if _anim:
        for _name, _data in _BUTTONS.items():
            _mi_name = 'HIVE_'+_name
            if cmds.menuItem(_mi_name, query=True, exists=True):
                cmds.deleteUI(_mi_name)
            lprint(' - ADDING', _mi_name, verbose=verbose)
            cmds.menuItem(
                _mi_name, parent=_anim,
                command=_data['cmd'], image=_data['image'],
                label=_data['label'])


def _install_psyhive_elements():
    """Install tools to PsyHive menu and shelf."""
    _menu = ui.obtain_menu('PsyHive', replace=True)
    ui.add_shelf('PsyHive')

    # Add shared buttons
    for _name, _data in _BUTTONS.items():
        cmds.menuItem(
            command=_data['cmd'], image=_data['image'], label=_data['label'])
        ui.add_shelf_button(
            'PsyHive_'+_name, command=_data['cmd'], image=_data['image'],
            parent='PsyHive', annotation=_data['label'])

    # Catch fail to install tools for offsite (eg. LittleZoo)
    for _idx, _grp in enumerate((
            [_ph_add_batch_cache,
             _ph_add_batch_rerender,
             _ph_add_yeti_tools,
             _ph_add_oculus_quest_toolkit],
            [_ph_add_anim_toolkit,
             _ph_add_tech_anim_toolkit])):
        for _func in _grp:
            try:
                _func(menu=_menu)
            except ImportError:
                print ' - ADD MENU ITEM FAILED:', _func
        cmds.menuItem(parent=_menu, divider=True)
        ui.add_separator(
            name='PsyHive_GroupSeparator{:d}'.format(_idx), parent='PsyHive')

    # Add show toolkits
    _ph_add_show_toolkits(_menu)

    # Add reset settings
    cmds.menuItem(divider=True, parent=_menu)
    ui.add_separator(name='PsyHive_SeparatorUtils', parent='PsyHive')
    _cmd = '\n'.join([
        'import {} as qt'.format(qt.__name__),
        'qt.reset_interface_settings()',
    ]).format()
    _icon = icons.EMOJI.find('Shower')
    _label = 'Reset interface settings'
    cmds.menuItem(label=_label, command=_cmd, image=_icon, parent=_menu)
    ui.add_shelf_button(
        'PsyHive_ResetSettings', command=_cmd, image=_icon,
        parent='PsyHive', annotation=_label)

    # Add refresh
    _cmd = '\n'.join([
        'from maya import cmds',
        'import {} as refresh'.format(refresh.__name__),
        'import {} as startup'.format(__name__),
        'refresh.reload_libs(verbose=2)',
        'cmds.evalDeferred(startup.user_setup)',
    ]).format()
    _icon = icons.EMOJI.find('Counterclockwise Arrows Button')
    cmds.menuItem(label='Reload libs', command=_cmd, parent=_menu, image=_icon)
    ui.add_shelf_button(
        'PsyHive_ReloadLibs', command=_cmd, image=_icon,
        parent='PsyHive', annotation='Reload libs')

    return _menu


def _ph_add_batch_cache(menu):
    """Add psyhive batch cache tool.

    Args:
        menu (str): menu to add to
    """
    from maya_psyhive.tools import batch_cache
    _cmd = '\n'.join([
        'import {} as batch_cache',
        'batch_cache.launch()']).format(batch_cache.__name__)
    cmds.menuItem(
        parent=menu, command=_cmd, image=batch_cache.ICON, label='Batch cache')
    ui.add_shelf_button(
        'PsyHive_BatchCache', command=_cmd, image=batch_cache.ICON,
        parent='PsyHive', annotation='Batch cache')


def _ph_add_batch_rerender(menu):
    """Add psyhive batch rerender tool.

    Args:
        menu (str): menu to add to
    """
    from psyhive.tools import batch_rerender
    _cmd = '\n'.join([
        'import {} as batch_rerender',
        'batch_rerender.launch()']).format(batch_rerender.__name__)
    cmds.menuItem(
        parent=menu, command=_cmd, image=batch_rerender.ICON,
        label='Batch rerender')
    ui.add_shelf_button(
        'PsyHive_BatchRerender', command=_cmd, image=batch_rerender.ICON,
        parent='PsyHive', annotation='Batch rerender')


def _ph_add_yeti_tools(menu):
    """Add psyhive yeti tools option.

    Args:
        menu (str): menu to add to
    """
    from maya_psyhive.tools import yeti
    _cmd = '\n'.join([
        'import {} as yeti',
        'yeti.launch_cache_tools()']).format(yeti.__name__)
    cmds.menuItem(
        parent=menu, command=_cmd, image=yeti.ICON, label='Yeti cache tools')
    ui.add_shelf_button(
        'PsyHive_YetiTools', command=_cmd, image=yeti.ICON,
        parent='PsyHive', annotation='Yeti cache tools')


def _ph_add_oculus_quest_toolkit(menu):
    """Add psyhive oculus quest toolkit option.

    Args:
        menu (str): menu to add to
    """
    from maya_psyhive.tools import oculus_quest
    _cmd = '\n'.join([
        'import {} as oculus_quest',
        'oculus_quest.launch()']).format(oculus_quest.__name__)
    cmds.menuItem(
        parent=menu, command=_cmd, image=icons.EMOJI.find("Eye"),
        label='Oculus Quest toolkit')
    ui.add_shelf_button(
        'PsyHive_OculusToolkit', command=_cmd, image=icons.EMOJI.find("Eye"),
        parent='PsyHive', annotation='Oculus Quest toolkit')


def _ph_add_toolkit(menu, toolkit):
    """Add PsyHive toolkit option.

    Args:
        menu (str): menu to add to
        toolkit (mod): toolkit module to add
    """
    _name = getattr(
        toolkit, 'PYGUI_TITLE',
        to_nice(toolkit.__name__.split('.')[-1])+' tools')
    _cmd = '\n'.join([
        'import {} as toolkit',
        'import {} as py_gui',
        'py_gui.MayaPyGui(toolkit.__file__)']).format(
            toolkit.__name__, py_gui.__name__)
    cmds.menuItem(
        parent=menu, command=_cmd, image=toolkit.ICON, label=_name)
    py_gui.MayaPyShelfButton(mod=toolkit, parent='PsyHive', image=toolkit.ICON,
                             label=_name)


def _ph_add_anim_toolkit(menu):
    """Add PsyHive Anim toolkit option.

    Args:
        menu (str): menu to add to
    """
    from maya_psyhive.toolkits import anim
    _ph_add_toolkit(menu=menu, toolkit=anim)


def _ph_add_tech_anim_toolkit(menu):
    """Add PsyHive TechAnim toolkit option.

    Args:
        menu (str): menu to add to
    """
    from maya_psyhive.toolkits import tech_anim
    _ph_add_toolkit(menu=menu, toolkit=tech_anim)


def _ph_add_show_toolkits(parent):
    """Add show toolkits options.

    Args:
        parent (str): parent menu
    """
    _shows = cmds.menuItem(
        label='Shows', parent=parent, subMenu=True,
        image=icons.EMOJI.find('Top Hat'))

    _shows_dir = File(shows.__file__).parent()
    for _py in _shows_dir.find(extn='py', depth=1, type_='f'):

        _file = PyFile(_py)
        if _file.basename.startswith('_'):
            continue

        _mod = _file.get_module()
        _rand = str_to_seed(_file.basename)
        _icon = getattr(_mod, 'ICON', _rand.choice(icons.ANIMALS))
        _label = getattr(_mod, 'LABEL', to_nice(_file.basename))
        _title = '{} tools'.format(_label)
        _cmd = '\n'.join([
            'import {py_gui} as py_gui',
            '_path = "{file}"',
            '_title = "{title}"',
            'py_gui.MayaPyGui(_path, title=_title, all_defs=True)',
        ]).format(py_gui=py_gui.__name__, file=_file.path, title=_title)
        cmds.menuItem(command=_cmd, image=_icon, label=_label, parent=_shows)

        py_gui.MayaPyShelfButton(mod=_mod, parent='PsyHive', image=_icon,
                                 label=_label)


@track_usage
def user_setup():
    """User setup."""
    dprint('Executing PsyHive user setup')

    if cmds.about(batch=True):
        return

    _install_psyhive_elements()

    # Fix logging level (pymel sets to debug)
    _fix_fn = wrap_fn(logging.getLogger().setLevel, logging.WARNING)
    cmds.evalDeferred(_fix_fn, lowestPriority=True)

    # Add elements to psyop menu (deferred to make sure exists)
    cmds.evalDeferred(_add_elements_to_psyop_menu, lowestPriority=True)

    # Add script editor save to project
    cmds.evalDeferred(script_editor_add_project_opts)
