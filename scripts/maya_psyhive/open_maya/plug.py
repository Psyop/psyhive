"""Tools for manaing attribute plugs."""

import functools
import re

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import get_single, lprint
from maya_psyhive.utils import get_attr


def _nice_runtime_error(func):
    """Raise a better error in the case of a missing attribute.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _runtime_catch_fn(self, name, **kwargs):
        try:
            _result = func(self, name, **kwargs)
        except RuntimeError:
            raise RuntimeError('attribute not found - {}'.format(name))
        return _result

    return _runtime_catch_fn


class HPlug(om.MPlug):
    """Wrapper for MPlug object - represents an attribute."""

    @_nice_runtime_error
    def __init__(self, name):
        """Constructor.

        Args:
            name (str): attribute name (eg. persp.tx)
        """

        # Read node/attr name
        if not name.count('.') == 1:
            raise ValueError(name)
        self.name = name
        self.node, self.attr = name.split('.')

        _tmp = om.MSelectionList()
        _tmp.add(self.node)
        _obj = _tmp.getDependNode(0)
        _dep_node = om.MFnDependencyNode(_obj)

        # Create plug to MPlug init
        if '[' in self.attr:  # handle indexed attrs
            self.attr, _idx, _ = re.split(r'[\[\]]', self.attr)
            _idx = int(_idx)
            _parent = _dep_node.findPlug(self.attr, False)
            _plug = _parent.elementByLogicalIndex(_idx)
        else:
            _plug = _dep_node.findPlug(self.attr, False)
        super(HPlug, self).__init__(_plug)

    def break_connections(self, verbose=0):
        """Break incoming connections on this plug.

        Args:
            verbose (int): print process data
        """
        _conn = cmds.listConnections(
            self, destination=False, plugs=True, connections=True)
        if not _conn:
            return
        _dest, _src = _conn
        lprint('BREAK CONN', _src, _dest, verbose=verbose)
        cmds.disconnectAttr(_src, _dest)

    def connect(self, other, **kwargs):
        """Connect this plug to another one.

        Args:
            other (str|HPlug): target for connection
        """
        cmds.connectAttr(self, other, **kwargs)

    def get_attr(self):
        return get_attr(self.name)

    def find_anim(self):
        """Find any anim curve connected to this attribute.

        Returns:
            (MFnAnimCurve|None): anim curve (if any)
        """
        from maya_psyhive import open_maya as hom
        _anim = get_single(
            cmds.listConnections(
                self.node, type='animCurve', destination=False),
            catch=True)
        return hom.HFnAnimCurve(_anim) if _anim else None

    def list_connections(self, **kwargs):
        return cmds.listConnections(self, **kwargs)

    def set_attr(self, val):
        """Set the value of this attribute.

        Args:
            val (any): attribute value
        """
        cmds.setAttr(self.name, val)

    def set_keyframe(self, **kwargs):
        """Set keyframe on this attr."""
        cmds.setKeyframe(self, **kwargs)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{}:"{}">'.format(type(self).__name__, self.name)
