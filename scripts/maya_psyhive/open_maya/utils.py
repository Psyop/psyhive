"""General tools for open_maya module."""

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint, get_single
from maya_psyhive.utils import get_unique


class IndexedAttrGetter(object):
    """Class to build an indexed attr string for the given node and index.

    For example, this could be used to get mesh vtx names, or curve cvs.
    """

    def __init__(self, node, attr):
        """Constructor.

        Args:
            node (HFnDependencyNode): node to create attr for
            attr (str): attribute name
        """
        self.node = node
        self.attr = attr

    def __getitem__(self, idx):
        return self.node.plugs('{}[{:d}]'.format(self.attr, idx))


def build_arrow(name='arrow', length=0.3):
    """Geometry in an arrow shape.

    Args:
        name (str): name for arrow curve
        length (float): length of wings (base is length 1.0)

    Returns:
        (HFnNurbsCurve): arrow curve
    """
    import maya_psyhive.open_maya as hom
    return hom.CMDS.curve(name=name, degree=1, point=(
        hom.HPoint(0, 1-length, length),
        hom.Y_AXIS,
        hom.ORIGIN,
        hom.Y_AXIS,
        hom.HPoint(0, 1-length, -length),
    ))


def build_loc(name='locator', scale=None, col=None):
    """Build locator at this array's position.

    Args:
        name (str): name for locator
        scale (str): locator scale
        col (str): locator colour

    Returns:
        (str): locator name
    """
    from maya_psyhive import open_maya as hom
    from maya_psyhive.utils import set_col

    _loc = cmds.spaceLocator(name=get_unique(name))[0]

    # Apply scale
    _scale = scale or hom.LOC_SCALE
    if _scale != 1.0:
        _shp = get_single(cmds.listRelatives(_loc, shapes=True))
        cmds.setAttr(
            _shp+'.localScale', _scale, _scale, _scale)

    # Apply colour
    _col = col or hom.LOC_COL
    set_col(_loc, _col)

    return hom.HFnTransform(_loc)


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
        if isinstance(_result, float):
            return _result
        elif isinstance(_result, om.MPoint):
            return hom.HPoint(_result)
        elif isinstance(_result, om.MVector):
            return hom.HVector(_result)
        elif isinstance(_result, om.MMatrix):
            return hom.HMatrix(_result)
        raise ValueError(_result)

    return _casted_result_fn
