"""Tools for managing maya interface."""

from maya import cmds, mel, OpenMayaUI

from psyhive import qt
from psyhive.utils import lprint


def get_main_window():
    """Get maya main window ui element name."""
    return mel.eval('$s=$gMainWindow', verbose=0)


def get_main_window_ptr():
    """Get pointer for main maya window.

    Returns:
        (QWidget): wrapped instance
    """
    import shiboken2
    _maya_win = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(long(_maya_win), qt.QtWidgets.QWidget)


def obtain_menu(name, replace=False, verbose=0):
    """Find a menu element with the given name.

    If it doesn't exist, it is create.

    Args:
        name (str): name of menu element to search for
        replace (bool): replace any existing element
    """
    lprint('SEARCHING FOR', name, verbose=verbose)

    # Find parent menu
    for _menu in cmds.lsUI(menus=True):
        _label = cmds.menu(_menu, query=True, label=True)
        lprint(' - TESTING', _menu, _label, verbose=verbose)
        if _label == name:
            lprint(' - MATCHED', verbose=verbose)
            if replace:
                lprint(' - DELETING', _menu, verbose=verbose)
                cmds.deleteUI(_menu)
                break
            else:
                return _menu

    # Create if not found
    return cmds.menu(
        name+"_MENU", label=name, tearOff=True, parent=get_main_window())


def populate_option_menu(name, choices):
    """Populate an option menu.

    Args:
        name (str): option menu name
        choices (list): option menu choices
    """

    # Remove existing
    _items = cmds.optionMenu(
        name, query=True, itemListLong=True)
    if _items:
        cmds.deleteUI(_items)

    # Add choices
    for _choice in choices:
        cmds.menuItem(label=_choice, parent=name)


def read_option_menu(name, type_):
    """Read the selected item in an option menu.

    Args:
        name (str): option menu to read
        type_ (type): type of result to obtain

    Returns:
        (any): selected item if given type
    """
    _type = type_ or str
    _sel = cmds.optionMenu(name, query=True, select=True)
    _items = cmds.optionMenu(name, query=True, itemListLong=True)
    _item = _items[_sel-1]
    _text = cmds.menuItem(_item, query=True, label=True)
    return _type(_text)


def set_option_menu(name, value):
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
