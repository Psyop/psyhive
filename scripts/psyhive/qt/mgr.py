"""Tools for managing import QtCore/QtGui/QtWidgets from parent module.

This allows PySide or PySide2 to be used transparently.
"""

try:
    from Qt import QtUiTools, QtCore, QtGui, QtWidgets
except ImportError:
    from PySide import QtUiTools, QtCore, QtGui
    from PySide import QtGui as QtWidgets
