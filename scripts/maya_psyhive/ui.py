"""Tools for managing maya interface."""

from maya import cmds, mel


def get_main_window():
    """Get maya main window ui element name."""
    return mel.eval('$s=$gMainWindow', verbose=0)


def obtain_menu(name, replace=False):
    """Find a menu element with the given name.

    If it doesn't exist, it is create.

    Args:
        name (name): name of menu element to search for
        replace (bool): replace any existing element
    """

    # Find parent menu
    for _menu in cmds.lsUI(menus=True):
        _label = cmds.menu(_menu, query=True, label=True)
        if _label == name:
            if replace:
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
    _sel = cmds.optionMenu(name, query=True, select=True)
    _items = cmds.optionMenu(name, query=True, itemListLong=True)
    _item = _items[_sel-1]
    _text = cmds.menuItem(_item, query=True, label=True)
    return type_(_text)


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
