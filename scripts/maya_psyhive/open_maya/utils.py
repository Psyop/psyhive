"""General tools for open_maya module."""

import math
import random

from maya import cmds
from maya.api import OpenMaya as om

from psyhive import qt
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


def find_anim(filter_=None):
    """Find anim curves in this scene.

    Args:
        filter_ (str): filter to pass to ls comment

    Returns:
        (HFnAnimCurve list): anim curves
    """
    from maya_psyhive import open_maya as hom
    return find_nodes(
        type_='animCurve', class_=hom.HFnAnimCurve, filter_=filter_)


def find_cams():
    """Find scene cameras.

    Returns:
        (HFnCamera list): cameras
    """
    from maya_psyhive import open_maya as hom
    return [hom.HFnCamera(_shp.get_parent())
            for _shp in find_nodes(type_='camera')]


def find_node(type_=None, namespace=None):
    """Find single matching node in current scene.

    Args:
        type_ (str): filter by type
        namespace (str): filter by namespace

    Returns:
        (HFnDependencyNode): matching node
    """
    return get_single(find_nodes(type_=type_, namespace=namespace))


def find_nodes(filter_=None, class_=None, type_=None, long_=False,
               selection=False, namespace=None):
    """Find nodes on the current scene (uses ls command).

    Args:
        filter_ (str): filter in ls format (eg. "tmp:*")
        class_ (class): override node class (default is HFnDepdendencyNode)
        type_ (str): ls type flag
        long_ (bool): ls long flag
        selection (bool): seach only selected nodes
        namespace (str): filter by namespace

    Returns:
        (HFnDepdendencyNode list): nodes
    """
    from maya_psyhive import open_maya as hom

    _class = class_ or hom.HFnDependencyNode
    _args = [filter_] if filter_ else []

    _kwargs = {'long': long_, 'selection': selection}
    if type_:
        _kwargs['type'] = type_

    _results = []
    for _node in cmds.ls(*_args, **_kwargs):
        try:
            _result = _class(_node)
        except RuntimeError:
            continue
        if namespace is not None and not _result.namespace == namespace:
            continue
        _results.append(_result)
    return _results


def find_tfms(class_=None):
    """Find scene transforms.

    Args:
        class_ (class): override node class (default is HFnTransform)

    Returns:
        (HFnTransform list): transforms
    """
    from maya_psyhive import open_maya as hom
    _class = class_ or hom.HFnTransform
    return find_nodes(type_='transform', class_=_class)


def get_col(col):
    """Get an OpenMaya colour object.

    This can be used to get a colour from a name (eg. Cyna, IndianRed)
    or a QColor.

    Args:
        col (str|QColor): colour to create

    Returns:
        (MColor): OpenMaya colour
    """
    _q_col = qt.get_col(col)
    return om.MColor(_q_col.to_tuple('float'))


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
        (HFnPlug|HPlug list): if class_ is HPlug
    """
    from maya_psyhive import open_maya as hom

    # Build list of selected nodes
    _results = []
    for _node in hom.CMDS.ls(selection=True):

        _result = _node
        _type = _node.object_type()
        lprint('TESTING', _node, verbose=verbose > 1)

        # Map transforms to HFnTransform
        if _type == 'transform':
            _result = hom.HFnTransform(str(_node))

        # Apply type filter
        if type_:
            if type_ != 'transform' and _type == 'transform' and _result.shp:
                _type = _result.shp.object_type()
                lprint(' - SHAPE TYPE', _type, verbose=verbose > 1)
            if not _type == type_:
                lprint(' - REJECTED', type_, _type, verbose=verbose > 1)
                continue

        if class_ is hom.HPlug:
            for _attr in cmds.channelBox(
                    'mainChannelBox', query=True,
                    selectedMainAttributes=True) or []:
                _plug = hom.HPlug('{}.{}'.format(_node, _attr))
                _results.append(_plug)
            continue
        elif class_:
            try:
                _result = class_(str(_node))
            except ValueError:
                lprint(' - CLASS FAIL', class_, verbose=verbose > 1)
                continue

        lprint(' - ADDED', verbose=verbose > 1)
        _results.append(_result)

    # Get result
    if multi:
        return _results
    return get_single(_results, name='selected object', verbose=verbose)


def lerp(fr_, pt1, pt2):
    """Linear interpolate between two points.

    Args:
        fr_ (float): interpolation fraction
        pt1 (HPoint): start point
        pt2 (HPoint): end point

    Returns:
        (HPoint): interpolated point
    """
    return pt1 + (pt2 - pt1) * fr_


def read_connections(obj, incoming=True, outgoing=True, class_=None):
    """Read connections on the given plug/node.

    Args:
        obj (str): object to read
        incoming (bool): include incoming connections
        outgoing (bool): include outgoing connections
        class_ (class): override plug class (eg. str)

    Returns:
        (HPlug tuple list): list of plug pairs
    """
    _conns = []
    if incoming:
        _conns += read_incoming(obj, class_=class_)
    if outgoing:
        _conns += read_outgoing(obj, class_=class_)
    return _conns


def read_incoming(obj, class_=None, type_=None):
    """Read incoming connections to the given plug/node.

    Args:
        obj (str): object to read
        class_ (class): override plug class (eg. str)
        type_ (str): filter by type

    Returns:
        (HPlug tuple list): list of plug pairs
    """
    from .. import open_maya as hom
    _class = class_ or hom.HPlug
    _conns = []
    _kwargs = {}
    if type_:
        _kwargs['type'] = type_
    _data = cmds.listConnections(
        obj, destination=False, plugs=True, connections=True, **_kwargs)
    while _data:
        _src, _trg = _class(_data.pop()), _class(_data.pop())
        _conns.append((_src, _trg))
    return _conns


def read_outgoing(obj, class_=None, type_=None):
    """Read outgoing connections from the given plug/node.

    Args:
        obj (str): object to read
        class_ (class): override plug class (eg. str)
        type_ (str): filter by type

    Returns:
        (HPlug tuple list): list of plug pairs
    """
    from .. import open_maya as hom
    _class = class_ or hom.HPlug
    _conns = []
    _kwargs = {}
    if type_:
        _kwargs['type'] = type_
    _data = cmds.listConnections(
        obj, source=False, plugs=True, connections=True, **_kwargs)
    while _data:
        _trg, _src = _class(_data.pop()), _class(_data.pop())
        _conns.append((_src, _trg))
    return _conns


def set_locator_scale(value):
    """Set locator scale global.

    Args:
        value (float): scale to apply
    """
    from maya_psyhive import open_maya as hom
    hom.LOC_SCALE = value


def sph_rand():
    """Generate a random point on a sphere.

    Returns:
        (mom.MPoint): random point
    """
    from maya_psyhive import open_maya as hom
    _theta = random.random()*2*math.pi
    _phi = random.random()*math.pi
    return hom.HPoint(
        math.cos(_theta) * math.sin(_phi),
        math.sin(_theta) * math.sin(_phi),
        math.cos(_phi))
