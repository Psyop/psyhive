"""Wrappers for QtCore objects."""

from ..qtw_mgr import QtCore


class HRect(QtCore.QRect):
    """Wrapper for QRect."""

    def aspect(self):
        """Get aspect ratio of this rect.

        Returns:
            (float): aspect ration
        """
        return 1.0 * self.width() / self.height()

    def __repr__(self):
        return '<{}({:d}, {:d}, {:d}, {:d})>'.format(
            type(self).__name__,
            self.topLeft().x(), self.topLeft().y(),
            self.size().width(), self.size().height())
