"""Tools for wrapping maya.cmds to open_maya inputs/outputs."""

import functools

from maya import cmds

from psyhive.utils import lprint
from maya_psyhive.utils import get_unique
from maya_psyhive.open_maya.base_array3 import BaseArray3
from maya_psyhive.open_maya.base_node import BaseNode


def _clean_item(item, verbose=0):
    """Convert the given item to a maya friendly version.

    HPoint/HVector objects are converted to tuple.

    Args:
        item (any): item to clean
        verbose (int): print process data

    Returns:
        (any): cleaned item
    """
    from maya_psyhive import open_maya as hom

    if isinstance(item, (tuple, list)):
        lprint("CLEAING LIST", item, verbose=verbose)
        return [_clean_item(_item, verbose=verbose) for _item in item]
    elif isinstance(item, (BaseArray3, hom.HPoint, hom.HVector)):
        lprint("CLEAING ARRAY3", item, verbose=verbose)
        return item.to_tuple()
    elif isinstance(item, BaseNode):
        return str(item)
    lprint("NO CLEAN REQUIRED", item, verbose=verbose)
    return item


def _get_result_mapper(func, list_idx=None, class_=None, verbose=0):
    """Get result mapper decorator.

    The faciliates the mapping of a maya.cmds function to open_maya
    output.

    Args:
        func (fn): function to map
        list_idx (int): indicates the result is a list and this index
            item should be returned
        class_ (type): convert the result to this class
        verbose (int): print process data

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _result_mapper(*args, **kwargs):

        lprint('EXECUTING', func.__name__, verbose=verbose)

        # Clean kwargs
        _kwargs = kwargs
        for _key, _val in kwargs.items():
            _clean_val = _clean_item(_val)
            _kwargs[_key] = _clean_val
            lprint('   -', _key, _val, '->', _clean_val, verbose=verbose)

        # Apply get_unique
        if 'name' in _kwargs:
            _kwargs['name'] = get_unique(_kwargs['name'])

        lprint(' - KWARGS', _kwargs, verbose=verbose)
        _result = func(*args, **_kwargs)
        lprint(' - INITIAL RESULT', _result, type(_result), verbose=verbose)

        if list_idx is not None:
            _result = _result[list_idx]
        if class_:
            _result = class_(_result)

        lprint(' - RESULT', _result, type(_result), verbose=verbose)
        return _result

    return _result_mapper


class _CmdsMapper(object):
    """Maps maya.cmds functions to open_maya inputs/outputs.

    For example CMDS.circle can take HPoint inputs and returns a
    HFnNurbsCurve object.
    """

    def __getattr__(self, name):
        from maya_psyhive import open_maya as hom
        _fn = getattr(cmds, name)
        if name in ['circle']:
            return _get_result_mapper(
                _fn, list_idx=0, class_=hom.HFnNurbsCurve)
        elif name in ['curve']:
            return _get_result_mapper(
                _fn, class_=hom.HFnNurbsCurve)
        elif name in ['sphere', 'loft']:
            return _get_result_mapper(
                _fn, list_idx=0, class_=hom.HFnNurbsSurface)
        elif name in ['createNode', 'pathAnimation']:
            return _get_result_mapper(
                _fn, class_=hom.HFnDependencyNode)
        raise ValueError(name)


CMDS = _CmdsMapper()
