"""TOols for building a python file into an interface."""

from psyhive import host

from psyhive.py_gui.install import install_gui, Section, ArgUpdater
if host.NAME == 'maya':
    from psyhive.py_gui.maya_ import MayaPyGui
