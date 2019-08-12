"""Override for QtGui.QColor."""

from psyhive.qt.wrapper.mgr import QtGui


class HColor(QtGui.QColor):
    """Override for QColor."""

    def blacken(self, val):
        """Whiten this colour by the given fraction (1 returns white).

        Args:
            val (float): whiten fraction

        Returns:
            (HColor): whitened colour
        """
        return self*(1-val) + HColor('black')*val

    def to_tuple(self, mode='int'):
        """Get this colour's RGB data as a tuple.

        Args:
            mode (str): colour mode (int or float)

        Returns:
            (tuple): RGB values
        """
        if mode == 'int':
            return self.red(), self.green(), self.blue()
        elif mode == 'float':
            return self.red()/255.0, self.green()/255.0, self.blue()/255.0
        raise ValueError(mode)

    def whiten(self, val):
        """Whiten this colour by the given fraction (1 returns white).

        Args:
            val (float): whiten fraction

        Returns:
            (HColor): whitened colour
        """
        return self*(1-val) + HColor('white')*val

    def __add__(self, other):
        return HColor(
            self.red() + other.red(),
            self.green() + other.green(),
            self.blue() + other.blue())

    def __mul__(self, value):
        return HColor(
            self.red() * value,
            self.green() * value,
            self.blue() * value)

    def __str__(self):
        return '<{}:({})>'.format(
            type(self).__name__,
            ', '.join(['{:d}'.format(_val) for _val in self.to_tuple()]))

    def __sub__(self, other):
        return HColor(
            self.red() - other.red(),
            self.green() - other.green(),
            self.blue() - other.blue())
