"""General tools for open_maya module."""

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint
from maya_psyhive.utils import get_unique


def cast_result(func, verbose=0):
    """Decorator to typecast the result of a function.

    This is used to convert a maya.api.OpenMaya object to a
    maya_psyhive.open_maya object.

    Args:
        func (fn): function to decorate
        verbose (int): print process data
    """

    def _casted_result_fn(*args, **kwargs):

        import maya_psyhive.open_maya as hom

        _result = func(*args, **kwargs)
        lprint('CASTING RESULT', _result, verbose=verbose)
        if isinstance(_result, om.MPoint):
            return hom.HPoint(_result)
        elif isinstance(_result, om.MVector):
            return hom.HVector(_result)
        raise ValueError(_result)

    return _casted_result_fn


class HArray3Base(object):
    """Base class for any 3d array object."""

    def apply_to(self, node):
        """Apply this data to the given node.

        Args:
            node (str): node to apply to
        """
        # from maya_psyhive import open_maya as hom
        # _piv = hom.HPoint(cmds.getAttr(node+'.rotatePivot')[0])
        # print 'APPLY TO', self, _piv
        # _pos = self - _piv
        cmds.xform(
            node, translation=self.to_tuple(), worldSpace=True)

    def build_loc(self, name=None):
        """Build locator at this array's position.

        Args:
            name (str): name for locator

        Returns:
            (str): locator name
        """
        _name = name or type(self).__name__.strip('_')
        _loc = cmds.spaceLocator(name=get_unique(_name))[0]
        self.apply_to(_loc)
        return _loc

    def to_tuple(self):
        """Convert this array to a tuple.

        Returns:
            (float tuple): 3 floats
        """
        return tuple([self[_idx] for _idx in range(3)])

    def __str__(self):
        return '<{}:({})>'.format(
            type(self).__name__.strip('_'),
            ', '.join(
                ['{:.03f}'.format(_val) for _val in self.to_tuple()]))

    def __sub__(self, other):
        from maya_psyhive import open_maya as hom
        return hom.HVector(
            self[0]-other[0], self[1]-other[1], self[2]-other[2])

    __repr__ = __str__
