"""Tools for managing import QtCore/QtGui/QtWidgets from parent module.

This allows PySide or PySide2 to be used transparently.

To allow this library to be used by LittleZoo, Qt/Qt_py is not used.
"""

try:
    from PySide2 import QtUiTools, QtCore, QtGui, QtWidgets
except ImportError:
    from PySide import QtUiTools, QtCore, QtGui
    from PySide import QtGui as QtWidgets

X_AXIS = QtCore.QPoint(1, 0)
Y_AXIS = QtCore.QPoint(0, 1)
