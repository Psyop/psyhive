"""TOols for building a python file into an interface."""

from psyhive import host

from psyhive.py_gui.install import (
    install_gui, set_section, ArgUpdater, hide_from_gui)
from psyhive.py_gui.qt_ import QtPyGui
if host.NAME == 'maya':
    from psyhive.py_gui.maya_ import MayaPyGui, get_selection_reader
