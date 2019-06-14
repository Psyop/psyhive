"""Base class for any 3d array (ie. point/vector)."""

from maya import cmds


class BaseArray3(object):
    """Base class for any 3d array object."""

    def apply_to(self, node, use_constraint=False):
        """Apply this data to the given node.

        Args:
            node (str): node to apply to
            use_constraint (bool): use locator and point constraint to apply
                position, deleting them after use - this seems more reliable
                in some cases but is slower
        """
        if use_constraint:
            _loc = self.build_loc()
            _cons = cmds.pointConstraint(
                _loc, node, maintainOffset=False)[0]
            cmds.delete(_cons, _loc)
            return

        cmds.xform(
            node, translation=self.to_tuple(), worldSpace=True)

    def build_loc(self, name=None, scale=None, col=None):
        """Build locator at this array's position.

        Args:
            name (str): name for locator
            scale (str): locator scale
            col (str): locator colour

        Returns:
            (str): locator name
        """
        from maya_psyhive import open_maya as hom
        _name = name or type(self).__name__.strip('_')
        _loc = hom.build_loc(name=_name, scale=scale, col=col)
        self.apply_to(_loc)
        return _loc

    def to_tuple(self):
        """Convert this array to a tuple.

        Returns:
            (float tuple): 3 floats
        """
        return tuple([self[_idx] for _idx in range(3)])

    def __add__(self, other):
        from maya_psyhive import open_maya as hom
        return hom.HVector(
            self[0]+other[0], self[1]+other[1], self[2]+other[2])

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
