"""Tools for managing maya interface."""

import tempfile

from maya import cmds, mel, OpenMayaUI

from psyhive import qt, icons
from psyhive.qt import QtWidgets
from psyhive.utils import lprint, store_result


class _ShelfButton(object):
    """Represents a shelf button."""

    def __init__(self, name):
        """Constructor.

        Args:
            name (str): button ui element name
        """
        self.name = name
        self.image = cmds.shelfButton(name, query=True, image=True)
        self.command = cmds.shelfButton(name, query=True, command=True)
        self.parent = cmds.shelfButton(name, query=True, parent=True)

    def delete(self):
        """Delete this button."""
        cmds.deleteUI(self.name)


def _find_shelf_buttons():
    """Find existing shelf buttons.

    Returns:
        (ShelfButton list): all shelf buttons
    """
    _btns = []
    for _ctrl in sorted(cmds.lsUI(controls=True)):
        if not cmds.shelfButton(_ctrl, query=True, exists=True):
            continue
        _btn = _ShelfButton(_ctrl)
        _btns.append(_btn)

    return _btns


def add_shelf(name, verbose=0):
    """Make sure the shelf of the given name exists.

    Args:
        name (str): name of shelf
        verbose (int): print process data

    Returns:
        (str): shelf name
    """

    _layout_name = name.replace(' ', '_')

    # Check if shelf exists
    _shelves = cmds.lsUI(type='shelfLayout')
    _exists = _layout_name in _shelves
    lprint('SHELF "{}" EXISTS: {}'.format(name, _exists), sorted(_shelves),
           verbose=verbose)

    if not _exists:

        # Get shelves parent
        _test_shelf = cmds.lsUI(type='shelfLayout')[0]
        lprint('TEST SHELF', _test_shelf, verbose=verbose)
        _parent = cmds.shelfLayout(_test_shelf, query=True, parent=True)
        lprint('PARENT', _parent, verbose=verbose)

        # Create the shelf
        lprint('BUILDING "{}" SHELF'.format(name), verbose=verbose)
        _layout_name = cmds.shelfLayout(name, parent=_parent)

    return _layout_name


def add_shelf_button(name, image, command, annotation=None, parent='Henry',
                     width=None, force=True, enabled=True):
    """Add a shelf button.

    Args:
        name (str): unique button name
        image (str): path to button image
        command (fn): button command
        annotation (str): button annotation (tooltip)
        parent (str): parent shelf
        width (int): button width
        force (bool): force replace any existing buttons
        enabled (bool): enabled state for button
    """

    # Replace existing buttons with matching name or command/image
    if cmds.shelfButton(name, query=True, exists=True):
        cmds.deleteUI(name)
    for _btn in _find_shelf_buttons():
        if _btn.image != image or _btn.command != command:
            continue
        if not force:
            qt.ok_cancel('Replace existing {} button?'.format(name))
        _btn.delete()

    # Create new button
    _kwargs = {}
    for _name, _val in [
            ('label', annotation),
            ('annotation', annotation),
            ('image', image),
            ('command', command),
            ('width', width),
            ('enable', enabled),
    ]:
        if _val:
            _kwargs[_name] = _val
    cmds.shelfButton(name, parent=parent, **_kwargs)


@store_result
def _get_separator_icon(icon='Fleur-de-lis'):
    """Build icon for shelf separator.

    Args:
        icon (str): emoji name for separator icon

    Returns:
        (str): path to tmp separator icon
    """
    _file = '{}/maya_psyhive/spacer_icon_{}.png'.format(
        tempfile.gettempdir(), icon)
    _pix = qt.HPixmap(70, 100)
    _pix.fill(qt.BLANK)

    _over = icons.EMOJI.find(icon)

    _pix.add_overlay(_over, pos=_pix.center(), resize=30, anchor='C')
    _pix.save_as(_file, force=True)
    return _file


def add_separator(name, parent, style='Fleur-de-lis'):
    """Add a shelf button separator.

    Args:
        name (str): ui element name
        parent (str): parent shelf
        style (str): separator style
    """
    if style == 'maya':
        if cmds.separator(name, exists=True):
            cmds.deleteUI(name)
        cmds.separator(name, style='shelf', parent=parent)
    elif style == 'Fleur-de-lis':
        _icon = _get_separator_icon()
        add_shelf_button(name, image=_icon, command='# {}\npass'.format(name),
                         width=10, parent=parent, annotation='** Separator **',
                         enabled=False)
    else:
        raise ValueError(style)


def clear_script_editor():
    """Clear script editor text."""
    _reporter = mel.eval('string $tmp = $gCommandReporter;')
    cmds.cmdScrollFieldReporter(_reporter, edit=True, clear=True)


def get_active_model_panel(as_editor=False, catch=False):
    """Get current active model panel.

    Args:
        as_editor (bool): return editor rather than panel
        catch (bool): no error on no/multi matches

    Returns:
        (str): ui element name
    """
    _panels = []
    _editors = []

    for _panel in cmds.lsUI(panels=True):
        if not cmds.modelPanel(_panel, query=True, exists=True):
            continue
        _editor = cmds.modelPanel(_panel, query=True, modelEditor=True)
        if cmds.modelEditor(_editor, query=True, activeView=True):
            _editors.append(_editor)
            _panels.append(_panel)

    if len(_panels) != 1 or len(_editors) != 1:
        if catch:
            return None
        raise RuntimeError("Could not read active model panel")

    return _editors[0] if as_editor else _panels[0]


def get_main_window():
    """Get maya main window ui element name."""
    return mel.eval('$s=$gMainWindow', verbose=0)


def get_main_window_ptr(style='oculus'):
    """Get pointer for main maya window.

    Args:
        style (str): how to read pointer

    Returns:
        (QWidget): wrapped instance
    """
    if style == 'generic':
        import shiboken2
        qt.get_application()  # Make sure there is QApplication
        _maya_win = OpenMayaUI.MQtUtil.mainWindow()
        return shiboken2.wrapInstance(long(_maya_win), QtWidgets.QWidget)
    elif style == 'oculus':
        app = QtWidgets.QApplication.instance()
        widgets = app.topLevelWidgets()
        for obj in widgets:
            if obj.objectName() == 'MayaWindow':
                return obj
        raise RuntimeError('Could not find MayaWindow instance')
    raise ValueError(style)


def obtain_menu(name, replace=False, verbose=0):
    """Find a menu element with the given name.

    If it doesn't exist, it is created.

    Args:
        name (str): name of menu element to search for
        replace (bool): replace any existing element
        verbose (int): print process data

    Returns:
        (str): menu ui element object name
    """
    lprint('SEARCHING FOR', name, verbose=verbose)

    # Find parent menu
    for _menu in cmds.lsUI(menus=True):
        _label = cmds.menu(_menu, query=True, label=True)
        lprint(' - TESTING name="{}" label="{}"'.format(_menu, _label),
               verbose=verbose)
        if _label == name:
            lprint(' - MATCHED', verbose=verbose)
            if replace:
                lprint(' - DELETING', _menu, verbose=verbose)
                cmds.deleteUI(_menu)
                break
            else:
                return _menu

    # Create if not found
    lprint(' - CREATING NEW MENU', verbose=verbose)
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
