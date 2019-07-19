"""Tools to be run on maya startup."""

import logging

from maya import cmds

from psyhive import icons, refresh, qt, py_gui
from psyhive.tools import track_usage
from psyhive.utils import (
    dprint, wrap_fn, get_single, lprint, File, str_to_seed)
from maya_psyhive import ui, shows
from maya_psyhive.tools import fkik_switcher
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


def _add_show_toolkits(parent):
    """Add show toolkits options.

    Args:
        parent (str): parent menu
    """
    _shows = cmds.menuItem(
        label='Shows', parent=parent, subMenu=True,
        image=icons.EMOJI.find('Lion'))

    _shows = File(shows.__file__).parent()
    print 'SHOWS', _shows
    for _py in _shows.find(extn='py', depth=1, type_='f'):
        _file = File(_py)
        if _file.basename.startswith('_'):
            continue
        print ' - ADDING FILE', _file
        _rand = str_to_seed(_file.basename)
        _icon = _rand.choice(icons.ANIMALS)
        _cmd = '\n'.join([
            'import {py_gui} as py_gui',
            '_path = "{file}"',
            '_title = "{title}"',
            'py_gui.MayaPyGui(_path, title=_title, all_defs=True)',
        ]).format(
            py_gui=py_gui.__name__, file=_file.path,
            title='{} tools'.format(_file.basename))
        cmds.menuItem(
            command=_cmd, image=_icon, label=_file.basename)

    # for


def _build_psyhive_menu():
    """Build psyhive menu."""
    _menu = ui.obtain_menu('PsyHive', replace=True)

    # Add shared buttons
    for _name, _data in _BUTTONS.items():
        cmds.menuItem(
            command=_data['cmd'], image=_data['image'], label=_data['label'])

    # Add batch cache (not available at LittleZoo)
    try:
        from maya_psyhive.tools import batch_cache
    except ImportError:
        pass
    else:
        _cmd = '\n'.join([
            'import {} as batch_cache',
            'batch_cache.launch()']).format(batch_cache.__name__)
        cmds.menuItem(
            command=_cmd, image=batch_cache.ICON, label='Batch cache')

    # Add show toolkits
    cmds.menuItem(divider=True)
    _add_show_toolkits(_menu)

    # Add reset settings
    cmds.menuItem(divider=True, parent=_menu)
    _cmd = '\n'.join([
        'import {} as qt'.format(qt.__name__),
        'qt.reset_interface_settings()',
    ]).format()
    cmds.menuItem(
        label='Reset interface settings', command=_cmd,
        image=icons.EMOJI.find('Shower'), parent=_menu)

    # Add refresh
    _cmd = '\n'.join([
        'from maya import cmds',
        'import {} as refresh'.format(refresh.__name__),
        'import {} as startup'.format(__name__),
        'refresh.reload_libs(verbose=2)',
        'cmds.evalDeferred(startup.user_setup)',
    ]).format()
    cmds.menuItem(
        label='Reload libs', command=_cmd, parent=_menu,
        image=icons.EMOJI.find('Counterclockwise Arrows Button'))

    return _menu


@track_usage
def user_setup():
    """User setup."""
    dprint('Executing PsyHive user setup')

    if cmds.about(batch=True):
        return

    _build_psyhive_menu()

    # Fix logging level (pymel sets to debug)
    _fix_fn = wrap_fn(logging.getLogger().setLevel, logging.WARNING)
    cmds.evalDeferred(_fix_fn, lowestPriority=True)

    # Add elements to psyop menu (deferred to make sure exists)
    cmds.evalDeferred(_add_elements_to_psyop_menu, lowestPriority=True)
