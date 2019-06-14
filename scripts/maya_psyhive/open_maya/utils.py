"""General tools for open_maya module."""

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint, get_single
from maya_psyhive.utils import get_unique


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
        if isinstance(_result, om.MPoint):
            return hom.HPoint(_result)
        elif isinstance(_result, om.MVector):
            return hom.HVector(_result)
        elif isinstance(_result, om.MMatrix):
            return hom.HMatrix(_result)
        raise ValueError(_result)

    return _casted_result_fn
