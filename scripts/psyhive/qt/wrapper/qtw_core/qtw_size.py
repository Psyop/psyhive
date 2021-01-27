"""Wrappers for QtCore objects."""

from ..qtw_mgr import QtCore


class HSize(QtCore.QSize):
    """Wrapper for QSize."""

    def to_tuple(self):
        """Get size as tuple.

        Returns:
            (int, int): width/height
        """
        return self.width(), self.height()

    def __repr__(self):
        return '<{}:{:d}x{:d}>'.format(
            type(self).__name__, self.width(), self.height())
