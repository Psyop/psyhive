"""Wrappers for QtCore objects."""

from psyhive.qt.wrapper.mgr import QtCore


class HPoint(QtCore.QPoint):
    """Wrapper for QPoint."""
    def __repr__(self):
        return '<{}({:d}, {:d})>'.format(
            type(self).__name__, self.x(), self.y())
