"""General tools for open_maya module."""

from maya.api import OpenMaya as om

from psyhive.utils import lprint


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
