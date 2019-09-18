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


def get_selected(type_=None, class_=None, multi=False, verbose=1):
    """Get selected node.

    Unless the multi flag is using, this will error if there isn't
    exactly one selected node matched.

    Args:
        type_ (str): filter nodes by type
        class_ (class): only return nodes that cast to this class
        multi (bool): return multiple nodes
        verbose (int): print process data

    Returns:
        (HFnDependencyNode): matching node
        (HFnDependencyNode list): matching nodes (if multi flag used)
    """
    from maya_psyhive import open_maya as hom

    # Build list of selected nodes
    _nodes = []
    for _node in hom.CMDS.ls(selection=True):

        _type = _node.object_type()
        lprint('TESTING', _node, verbose=verbose > 1)

        # Map transforms to HFnTransform
        if _type == 'transform':
            _node = hom.HFnTransform(str(_node))

        # Apply type filter
        if type_:
            if type_ != 'transform' and _type == 'transform' and _node.shp:
                _type = _node.shp.object_type()
                lprint(' - SHAPE TYPE', _type, verbose=verbose > 1)
            if not _type == type_:
                lprint(' - REJECTED', type_, _type, verbose=verbose > 1)
                continue

        if class_:
            try:
                _node = class_(str(_node))
            except ValueError:
                lprint(' - CLASS FAIL', class_, verbose=verbose > 1)
                continue

        lprint(' - ADDED', verbose=verbose > 1)
        _nodes.append(_node)

    # Get result
    if multi:
        return _nodes
    return get_single(_nodes, name='selected object', verbose=verbose)
