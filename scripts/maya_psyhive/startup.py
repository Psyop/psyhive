"""Tools to be run on maya startup."""

import logging

from maya import cmds, mel

from psyhive import icons, refresh, qt, py_gui, pipe
from psyhive.tools import track_usage
from psyhive.utils import (
    dprint, wrap_fn, get_single, lprint, File, str_to_seed, PyFile,
    write_file, to_nice)

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
        image=icons.EMOJI.find('Top Hat'))

    _shows = File(shows.__file__).parent()
    for _py in _shows.find(extn='py', depth=1, type_='f'):
        _file = PyFile(_py)
        if _file.basename.startswith('_'):
            continue
        _mod = _file.get_module()
        _rand = str_to_seed(_file.basename)
        _icon = getattr(_mod, 'ICON', _rand.choice(icons.ANIMALS))
        _label = getattr(_mod, 'LABEL', _file.basename)
        _title = '{} tools'.format(_label)
        _cmd = '\n'.join([
            'import {py_gui} as py_gui',
            '_path = "{file}"',
            '_title = "{title}"',
            'py_gui.MayaPyGui(_path, title=_title, all_defs=True)',
        ]).format(py_gui=py_gui.__name__, file=_file.path, title=_title)
        cmds.menuItem(command=_cmd, image=_icon, label=_label)


def _build_psyhive_menu():
    """Build psyhive menu."""
    _menu = ui.obtain_menu('PsyHive', replace=True)

    # Add shared buttons
    for _name, _data in _BUTTONS.items():
        cmds.menuItem(
            command=_data['cmd'], image=_data['image'], label=_data['label'])

    # Catch fail to install tools for offsite (eg. LittleZoo)
    for _grp in (
            [_ph_add_batch_cache,
             _ph_add_batch_rerender,
             _ph_add_yeti_tools,
             _ph_add_oculus_quest_toolkit],
            [_ph_add_anim_toolkit,
             _ph_add_tech_anim_toolkit]):
        for _func in _grp:
            try:
                _func()
            except ImportError:
                print ' - ADD MENU ITEM FAILED:', _func
        cmds.menuItem(divider=True)

    # Add show toolkits
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


def _ph_add_batch_cache():
    """Add psyhive batch cache tool."""
    from maya_psyhive.tools import batch_cache
    _cmd = '\n'.join([
        'import {} as batch_cache',
        'batch_cache.launch()']).format(batch_cache.__name__)
    cmds.menuItem(
        command=_cmd, image=batch_cache.ICON, label='Batch cache')


def _ph_add_batch_rerender():
    """Add psyhive batch rerender tool."""
    from psyhive.tools import batch_rerender
    _cmd = '\n'.join([
        'import {} as batch_rerender',
        'batch_rerender.launch()']).format(batch_rerender.__name__)
    cmds.menuItem(
        command=_cmd, image=batch_rerender.ICON, label='Batch rerender')


def _ph_add_yeti_tools():
    """Add psyhive yeti tools option."""
    from maya_psyhive.tools import yeti
    _cmd = '\n'.join([
        'import {} as yeti',
        'yeti.launch_cache_tools()']).format(yeti.__name__)
    cmds.menuItem(
        command=_cmd, image=yeti.ICON, label='Yeti cache tools')


def _ph_add_toolkit(toolkit):
    """Add PsyHive toolkit option.

    Args:
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
        command=_cmd, image=toolkit.ICON, label=_name)


def _ph_add_anim_toolkit():
    """Add PsyHive Anim toolkit option."""
    from maya_psyhive.toolkits import anim
    _ph_add_toolkit(anim)


def _ph_add_tech_anim_toolkit():
    """Add PsyHive TechAnim toolkit option."""
    from maya_psyhive.toolkits import tech_anim
    _ph_add_toolkit(tech_anim)


def _ph_add_oculus_quest_toolkit():
    """Add psyhive oculus quest toolkit option."""
    from maya_psyhive.tools import oculus_quest
    _cmd = '\n'.join([
        'import {} as oculus_quest',
        'oculus_quest.launch()']).format(oculus_quest.__name__)
    cmds.menuItem(
        command=_cmd, image=icons.EMOJI.find("Eye"),
        label='Oculus Quest toolkit')


def _script_editor_add_project_opts():
    """Add script editor project load/save option."""
    _menu = _script_editor_find_file_menu()

    # Add divider
    _div = 'psyProjectScriptDivider'
    if cmds.menuItem(_div, query=True, exists=True):
        cmds.deleteUI(_div)
    cmds.menuItem(_div, divider=True, parent=_menu, dividerLabel='Psyop')

    # Add open/save to project options
    for _name, _label, _func, _icon in [
            ('psyOpenFromProject',
             'Open from Project...',
             _script_editor_open_from_project,
             icons.OPEN),
            ('psySaveToProject',
             'Save to Project...',
             _script_editor_save_to_project,
             icons.SAVE),
    ]:
        if cmds.menuItem(_name, query=True, exists=True):
            cmds.deleteUI(_name)  # Replace existing
        cmds.menuItem(
            _name, label=_label, image=_icon, parent=_menu, command=_func)


def _script_editor_save_to_project(*xargs):
    """Execute save to project."""

    del xargs  # Maya callbacks require args

    # Get current editor
    _cur_editor = [
        _ui for _ui in cmds.lsUI(dumpWidgets=True, long=False)
        if cmds.cmdScrollFieldExecuter(_ui, query=True, exists=True)
        and not cmds.cmdScrollFieldExecuter(
            _ui, query=True, isObscured=True)][0]

    # Get file path
    _src_type = cmds.cmdScrollFieldExecuter(
        _cur_editor, query=True, sourceType=True)
    _extn = {'mel': 'mel', 'python': 'py'}[_src_type]
    _text = cmds.cmdScrollFieldExecuter(_cur_editor, query=True, text=True)
    _file = get_single(cmds.fileDialog2(
        fileMode=0,  # Single file doesn't need to exist
        caption="Save Script", okCaption='Save',
        startingDirectory=pipe.cur_project().maya_scripts_path,
        fileFilter='{} Files (*.{})'.format(_extn.upper(), _extn)), catch=True)

    # Write file to disk
    if _file:
        write_file(file_=_file, text=_text)


def _script_editor_open_from_project(*xargs):
    """Execute save to project."""
    del xargs  # Maya callbacks require args

    _cmd = '\n'.join([
        '$gLastUsedDir = "{}";'
        'handleScriptEditorAction "load";']).format(
            pipe.cur_project().maya_scripts_path)
    mel.eval(_cmd)


def _script_editor_find_file_menu(verbose=0):
    """Find script editor file menu.

    Args:
        verbose (int): print process data

    Returns:
        (str): script editor file menu name
    """

    # Find script editor file menu
    _menus = []
    for _menu in cmds.lsUI(menus=True):
        if cmds.menu(_menu, query=True, label=True) != 'File':
            continue
        lprint('TESTING', _menu, verbose=verbose)
        _post_cmd = cmds.menu(_menu, query=True, postMenuCommand=True)
        lprint(' - POST CMD', _post_cmd, verbose=verbose)
        if not _post_cmd or 'ScriptEditor' not in _post_cmd:
            continue
        lprint(' - MATCHED', verbose=verbose)
        _menus.append(_menu)

    _menu = get_single(_menus)

    # Init menu if it has no children
    if not cmds.menu(_menu, query=True, itemArray=True):
        _init_cmd = cmds.menu(_menu, query=True, postMenuCommand=True)
        mel.eval(_init_cmd)
        assert cmds.menu(_menu, query=True, itemArray=True)

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

    # Add script editor save to project
    cmds.evalDeferred(_script_editor_add_project_opts)
