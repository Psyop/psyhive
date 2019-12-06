"""Tools for building a py_gui using qt."""

import sys

import six

from psyhive import qt, icons, host
from psyhive.qt import QtWidgets, QtGui, Qt
from psyhive.utils import wrap_fn

from psyhive.py_gui import pyg_base

if not hasattr(sys, 'QT_PYGUI_INTERFACES'):
    sys.QT_PYGUI_INTERFACES = {}

_SECT_HEIGHT = 20


class QtPyGui(QtWidgets.QMainWindow, pyg_base.BasePyGui):
    """Interface built from a python file."""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Args:
            path (str): path to py file
        """
        if not host.NAME:
            qt.set_maya_palette()
        super(QtPyGui, self).__init__()
        pyg_base.BasePyGui.__init__(self, *args, **kwargs)

        self.resize(300, 64)
        self.show()

        # Maintain single instance
        if self.py_file.path in sys.QT_PYGUI_INTERFACES:
            try:
                sys.QT_PYGUI_INTERFACES[self.py_file.path].deleteLater()
            except RuntimeError:
                pass
        sys.QT_PYGUI_INTERFACES[self.py_file.path] = self

    def init_ui(self, rebuild_fn=None, verbose=0):
        """Initiate ui.

        Args:
            rebuild_fn (func): override rebuild function
            verbose (int): print process data
        """
        super(QtPyGui, self).init_ui(rebuild_fn=rebuild_fn)

        self.setWindowTitle(self.title)

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(3)
        self.main_widget.setLayout(self.main_layout)

        # Setup set window settings fns
        self.set_settings_fns['window']['Geometry']['width'] = (
            self._set_width)
        self.read_settings_fns['window']['Geometry']['width'] = (
            self.width)
        self.set_settings_fns['window']['Geometry']['height'] = (
            self._set_height)
        self.read_settings_fns['window']['Geometry']['height'] = (
            self.height)

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
        _widgets = []

        # Layout
        _h_layout = QtWidgets.QHBoxLayout()
        _h_layout.addStretch(1)
        _h_layout.setSpacing(3)
        self.main_layout.addLayout(_h_layout)

        # Label
        _label = QtWidgets.QLabel(label)
        _label.resize(label_width, 13)
        _label.setMinimumSize(_label.size())
        _label.setMaximumSize(_label.size())
        _policy = _label.sizePolicy()
        _policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Fixed)
        _label.setSizePolicy(_policy)
        _h_layout.addWidget(_label)
        _widgets.append(_label)

        # Field
        _field, _read_fn, _set_fn = self._add_arg_field(default, choices)
        _h_layout.addWidget(_field)
        _widgets.append(_field)

        # Update
        if update:

            _btn = qt.HPushButton(update.label)
            _btn.setMinimumSize(60, _SECT_HEIGHT)
            _btn.mousePressEvent = _get_update_fn(
                set_fn=_set_fn, update=update, field=_field)
            _h_layout.addWidget(_btn)
            _widgets.append(_btn)
            print 'ADDED BUTTON', _btn.size()

        if self.section:
            self._apply_section(*_widgets)

        return _read_fn, _set_fn

    def _add_arg_field(self, default, choices):
        """Add an editable arg field.

        Args:
            default (any): default value
            choices (list): options list

        Returns:
            (tuple): field object, read func, set func
        """
        if choices:
            _field = qt.HComboBox()
            for _idx, _choice in enumerate(choices):
                _field.addItem(str(_choice))
                _field.set_item_data(_idx, _choice)
            _field.select_data(default)
            _read_fn = _field.selected_data
            _set_fn = _field.select_data
        elif isinstance(default, six.string_types) or default is None:
            _field = QtWidgets.QLineEdit()
            if default:
                _field.setText(default)
            _read_fn = _field.text
            _set_fn = _field.setText
        elif isinstance(default, bool):
            _field = QtWidgets.QCheckBox()
            _field.setChecked(default)
            _field.setMinimumHeight(_SECT_HEIGHT)
            _read_fn = _field.isChecked
            _set_fn = _field.setChecked
        elif isinstance(default, int):
            _field = QtWidgets.QSpinBox()
            _field.setMinimum(-2000000000)
            _field.setMaximum(2000000000)
            _field.setValue(default)
            _read_fn = _field.value
            _set_fn = _field.setValue
        elif isinstance(default, float):
            _field = QtWidgets.QDoubleSpinBox()
            _field.setMinimum(-2000000000)
            _field.setMaximum(2000000000)
            _field.setValue(default)
            _read_fn = _field.value
            _set_fn = _field.setValue
        else:
            raise ValueError(default)

        _field.resize(1000, 13)
        _policy = _field.sizePolicy()
        _policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
        _policy.setHorizontalStretch(100)
        _field.setSizePolicy(_policy)

        return _field, _read_fn, _set_fn

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

        # Layout
        _h_layout = QtWidgets.QHBoxLayout()
        _h_layout.addStretch(1)
        _h_layout.setSpacing(3)
        self.main_layout.addLayout(_h_layout)

        # Code button
        _code = qt.HLabel()
        _code.mousePressEvent = code_fn
        _code.resize(depth, depth)
        _code.move(3, 23)
        _pix = qt.HPixmap(icon)
        _code.set_pixmap(_pix.resize(depth))
        _h_layout.addWidget(_code)

        # Button
        _btn = QtWidgets.QPushButton(label)
        _btn.mousePressEvent = exec_fn
        _policy = _btn.sizePolicy()
        _policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
        _policy.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
        _policy.setHorizontalStretch(100)
        _pal = _btn.palette()
        _col = QtGui.QColor(col)
        _pal.setColor(_pal.Button, _col)
        _text_col = QtGui.QColor('black' if _col.valueF() > 0.55 else 'white')
        _pal.setColor(_pal.ButtonText, _text_col)
        _btn.setAutoFillBackground(True)
        _btn.setPalette(_pal)
        _btn.setSizePolicy(_policy)
        _h_layout.addWidget(_btn)

        # Info button
        _info = qt.HLabel()
        _info.resize(depth, depth)
        _info.move(0, 20)
        _pix = qt.HPixmap(icons.EMOJI.find('Info'))
        _info.set_pixmap(_pix.resize(depth))
        _h_layout.addWidget(_info)

        _widgets = [_code, _btn, _info]

        if self.section:
            self._apply_section(*_widgets)

    def add_separator(self):
        """Add separator."""
        _line = QtWidgets.QFrame(self.main_widget)
        _line.setFrameShape(_line.HLine)
        _line.setFrameShadow(_line.Sunken)
        self.main_layout.addWidget(_line)
        self.main_layout.setAlignment(_line, Qt.AlignTop)
        if self.section:
            self._apply_section(_line)

    def add_menu(self, name):
        """Add menu to interface.

        Args:
            name (str): menu name
        """
        return self.menuBar().addMenu(name)

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
        print 'ADD MENU ITEM', parent, label
        _args = [label]
        if command:
            _args += [command]
        _action = parent.addAction(*_args)

        if image:
            _icon = qt.get_icon(image)
            _action.setIcon(_icon)

        if checkbox is not None:
            _action.setCheckable(True)
            _action.setChecked(checkbox)

    def _apply_section(self, *widgets):
        """Apply section to the given widgets."""
        for _widget in widgets:
            self.section.widgets.append(_widget)
            _widget.setVisible(not self.section.collapse)

    def set_section(self, section, verbose=0):
        """Set current section (implemented in subclass).

        Args:
            section (_Section): section to apply
            verbose (int): print process data
        """
        _section = _SectionHeader(
            section.label, col=self.section_col, collapse=section.collapse)
        _section.setMinimumSize(100, 22)
        _policy = _section.sizePolicy()
        _policy.setHorizontalPolicy(_policy.Expanding)
        _policy.setHorizontalStretch(100)
        _section.setSizePolicy(_policy)
        self.main_layout.addWidget(_section)

        self.read_settings_fns['section'][section.label] = {}
        self.read_settings_fns['section'][section.label]['collapse'] = wrap_fn(
            getattr, _section, 'collapse')

        self.set_settings_fns['section'][section.label] = {}
        self.set_settings_fns['section'][section.label]['collapse'] = wrap_fn(
            _section.set_collapse)

        self.section = _section

    def finalise_ui(self):
        """Finalise interface."""
        self.main_layout.addStretch(1)
        self.resize(300, 64)
        self.show()

    def _set_height(self, height):
        """Set window height.

        Args:
            height (int): height in pixels
        """
        self.resize(self.width(), height)

    def _set_width(self, width):
        """Set window width.

        Args:
            width (int): width in pixels
        """
        self.resize(width, self.height())

    def keyPressEvent(self, event):
        """Triggered by key press.

        Args:
            event (QKeyEvent): triggered event

        Returns:
            (bool): result
        """
        _result = super(QtPyGui, self).keyPressEvent(event)
        if event.key() == Qt.Key_Escape:
            self.deleteLater()
        return _result


class _SectionHeader(qt.HLabel):
    """Header for a collapsible section of defs.

    This mimics to formLayout element in maya - it has a triangle which
    points down when the section is unfolded (not collapse) and points
    to right when the section is folded (collapse). It also had a label
    for the section which appears to the right of the triangle.
    """

    def __init__(self, text, col, collapse=False):
        """Constructor.

        Args:
            text (str): section name
            col (QColor): section colour
            collapse (bool): collapse state of section
        """
        super(_SectionHeader, self).__init__()

        self.text = text
        self.col = col
        self.font = QtGui.QFont()
        self.font.setBold(True)
        self.collapse = collapse

        self.widgets = []

    def redraw_widgets(self):
        """Redraw child widgets."""
        self.update_pixmap()
        for _widget in self.widgets:
            _widget.setVisible(not self.collapse)

    def set_collapse(self, collapse=True):
        """Set collapse state of this section.

        Args:
            collapse (bool): collapse state
        """
        self.collapse = collapse
        self.redraw_widgets()

    def update_pixmap(self):
        """Update pixmap."""
        _pix = qt.HPixmap(self.size())
        _pix.fill(self.col)

        _text_col = 'Silver'
        _pix.add_text(
            self.text, pos=(30, self.height()/2), anchor='L',
            col=_text_col, font=self.font)

        _grid = self.height()/3
        if self.collapse:
            _pts = [(_grid*1.5, _grid*0.5),
                    (_grid*2.5, _grid*1.5),
                    (_grid*1.5, _grid*2.5)]
        else:
            _pts = [(_grid, _grid), (_grid*3, _grid), (_grid*2, _grid*2)]
        _pix.add_polygon(_pts, col=_text_col, outline=None)
        self.set_pixmap(_pix)

    def mousePressEvent(self, event):
        """Triggered by mouse press.

        Args:
            event (QMouseEvent): triggered event

        Returns:
            (bool): result
        """
        self.set_collapse(not self.collapse)
        return super(_SectionHeader, self).mousePressEvent(event)

    def resizeEvent(self, event):
        """Triggered resize event.

        Args:
            event (QResizeEvent): triggered event

        Returns:
            (bool): result
        """
        self.setMinimumSize(1, self.height())
        self.update_pixmap()
        return super(_SectionHeader, self).resizeEvent(event)


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
            field.clear()
            for _data in _choices:
                field.add_item(str(_data), data=_data)
            print 'UPDATED CHOICES', _default, _choices
        print 'SELECTING VALUE', _default
        set_fn(_default)

    return _update_fn
