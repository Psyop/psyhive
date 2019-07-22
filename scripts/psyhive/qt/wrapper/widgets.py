"""Qt widget overrides."""

from psyhive.utils import lprint

from psyhive.qt.wrapper.mgr import QtWidgets, QtGui, QtCore
from psyhive.qt.misc import get_col, get_pixmap, get_p, get_icon


def _dummy():
    """Function which does nothing - use for QMenu label."""


class HWidgetBase(object):
    """Base class for any override widget."""

    def get_c(self):
        """Get centre of this widget.

        Returns:
            (QPoint): centre
        """
        return self.pos() + get_p(self.size())/2

    def redraw(self, *args, **kwargs):
        """To be implemented replaced with redraw method."""

    def set_pixmap(self, pixmap):
        """Set pixmap for this widget.

        Args:
            pixmap (str|QPixmap): pixmap to apply
        """
        self.setPixmap(get_pixmap(pixmap))

    def set_icon(self, pixmap):
        """Set icon for this widget.

        Args:
            pixmap (str|QPixmap): pixmap to apply
        """
        _icon = QtGui.QIcon(get_pixmap(pixmap))
        self.setIcon(_icon)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.objectName())


class HCheckBox(QtWidgets.QCheckBox, HWidgetBase):
    """Override for QCheckBox widget."""


class HLabel(QtWidgets.QLabel, HWidgetBase):
    """Override for QLabel widget."""


class HListWidget(QtWidgets.QListWidget, HWidgetBase):
    """Override for QListWidget widget."""

    def all_data(self):
        """Get a list of all data stored in items.

        Returns:
            (any list): data list
        """
        return [
            _item.data(QtCore.Qt.UserRole) for _item in self.all_items()]

    def all_items(self):
        """Get a list of all items.

        Returns:
            (QListWidgetItem list): list of items
        """
        return [self.item(_idx) for _idx in range(self.count())]

    def all_text(self):
        """Get a list of all items text.

        Returns:
            (str list): item texts
        """
        return [str(_item.text()) for _item in self.all_items()]

    def select_data(self, items, verbose=0):
        """The items with text matching the given list.

        Args:
            items (str list): list of text of items to select
            verbose (int): print process data
        """
        lprint("SELECTING", self, items, verbose=verbose)
        for _item in self.all_items():
            _data = _item.get_data()
            lprint(" - TESTING", _data, _data in items, verbose=verbose)
            _item.setSelected(_data in items)

    def select_text(self, items, verbose=0):
        """The items with text matching the given list.

        Args:
            items (str): list of text of items to select
            verbose (int): print process data
        """
        lprint('SELECTING TEXT', items, verbose=verbose)
        for _item in self.all_items():
            _text = _item.text()
            lprint(' -', _text, _text in items, verbose=verbose)
            _item.setSelected(_text in items)

    def selected_data(self):
        """Get data stored in selected items.

        Returns:
            (any list): list of data
        """
        return [
            _item.data(QtCore.Qt.UserRole) for _item in self.selectedItems()]

    def selected_text(self):
        """Get selected item as text.

        Returns:
            (str list): text of selected items
        """
        return [_item.text() for _item in self.selectedItems()]


class HListWidgetItem(QtWidgets.QListWidgetItem):
    """Wrapper for QListWidgetItem object."""

    def get_data(self):
        """Get stored data from this item.

        Returns:
            (any): stored data
        """
        return self.data(QtCore.Qt.UserRole)

    def set_col(self, col):
        """Set text colour of this item.

        Args:
            col (str|QColor): colour to apply
        """
        _brush = QtGui.QBrush(get_col(col))
        self.setForeground(_brush)

    def set_data(self, data):
        """Set data for this widget item.

        Args:
            data (any): data to apply
        """
        self.setData(QtCore.Qt.UserRole, data)

    def set_icon(self, image):
        """Set icon for this item.

        Args:
            image (str|QPixmap): icon to apply
        """
        _icon = QtGui.QIcon(get_pixmap(image))
        self.setIcon(_icon)


class HMenu(QtWidgets.QMenu, HWidgetBase):
    """Override for QMenu widget."""

    def add_action(self, text, func, icon=None, verbose=0):
        """Add an action to the menu.

        Args:
            text (str): action text
            func (fn): action function
            icon (str|QPixmap): action icon
            verbose (int): print process data
        """
        _args = [text, func]
        if icon:
            _args = [get_pixmap(icon)] + _args
        lprint("ADD ACTION", _args, verbose=verbose)
        return self.addAction(*_args)

    def add_label(self, text, icon=None):
        """Add label to the menu.

        This is a disabled piece of text.

        Args:
            text (str): display text
            icon (str|QPixmap): icon
        """
        _action = self.add_action(text=text, func=_dummy, icon=icon)
        _action.setEnabled(0)
        return _action

    def add_menu(self, label, icon=None):
        """Add sub menu to this one.

        Args:
            label (str): label for sub menu
            icon (str|QPixmap): icon for menu

        Returns:
            (HMenu): menu instance
        """
        _menu = HMenu(label)
        if icon:
            _icon = get_icon(icon)
            _menu.setIcon(_icon)
        self.addMenu(_menu)
        return _menu


class HProgressBar(QtWidgets.QProgressBar, HWidgetBase):
    """Override for QProgressBar object."""

    def set_col(self, col):
        """Set colour for this progress bar.

        Args:
            col (str): colour to apply
        """
        _col = get_col(col)
        _palette = QtGui.QPalette()
        _brush = QtGui.QBrush(_col)
        for _state in [
                QtGui.QPalette.Active, QtGui.QPalette.Inactive]:
            _palette.setBrush(
                _state, QtGui.QPalette.Highlight, _brush)
        self.setPalette(_palette)


class HPushButton(QtWidgets.QPushButton, HWidgetBase):
    """Override for QPushButton object."""


class HTabWidget(QtWidgets.QTabWidget, HWidgetBase):
    """Override for QTabWidget object."""

    def cur_text(self):
        """Get text of the currently selected tab.

        Returns:
            (str): current tab title
        """
        _idx = self.currentIndex()
        return self.tabText(_idx)


class HTextBrowser(QtWidgets.QTextBrowser, HWidgetBase):
    """Override for QTextBrowser object."""


class HTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """Override for QTreeWidgetItem object."""

    _col = None

    def __init__(self, text, col=None, data=None):
        """Constructor.

        Args:
            text (str): display text
            col (str): text colour
            data (any): data to store with item
        """
        self._col = col or self._col
        super(HTreeWidgetItem, self).__init__()
        self.setText(0, text)
        if self._col:
            _brush = QtGui.QBrush(get_col(self._col))
            self.setForeground(0, _brush)
        if data:
            self.setData(0, QtCore.Qt.UserRole, data)

    def all_children(self):
        """Get a list of all children (including children's children).

        Returns:
            (QTreeWidgetItem list): all children
        """
        _all_children = []
        for _child in self.children():
            _all_children.append(_child)
            _all_children += _child.all_children()
        return _all_children

    def children(self):
        """Get a list of immediate children.

        Returns:
            (QTreeWidgetItem list): children
        """
        return [self.child(_idx) for _idx in range(self.childCount())]

    def get_data(self):
        """Get retrieve data from this item."""
        return self.data(0, QtCore.Qt.UserRole)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__.strip('_'), self.text(0))