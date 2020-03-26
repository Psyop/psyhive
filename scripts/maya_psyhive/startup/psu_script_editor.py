"""Tools for managing psyhive updates to the script editor.

This is adding the load/save to project options.
"""

from maya import cmds, mel

from psyhive import icons, pipe
from psyhive.utils import get_single, lprint, write_file


def script_editor_add_project_opts():
    """Add script editor project load/save option."""
    _menu = _script_editor_find_file_menu()
    if not _menu:
        return

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

    _menu = get_single(_menus, catch=True)
    if not _menu:
        print ' - PSYHIVE FAILED TO FIND SCRIPT EDITOR MENU'
        return None

    # Init menu if it has no children
    if not cmds.menu(_menu, query=True, itemArray=True):
        _init_cmd = cmds.menu(_menu, query=True, postMenuCommand=True)
        mel.eval(_init_cmd)
        assert cmds.menu(_menu, query=True, itemArray=True)

    return _menu
