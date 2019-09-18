"""Tools for manaing attribute plugs."""

import functools
import re

from maya import cmds
from maya.api import OpenMaya as om

from psyhive import qt
from psyhive.utils import get_single, lprint
from maya_psyhive.utils import (
    get_val, multiply_node, divide_node, add_node, set_val)


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

    def add_node(self, input_, output=None):
        """Connect this plug as the first input in an add node.

        Args:
            input_ (HPlug): second input
            output (HPlug): plug to connect output to

        Returns:
            (HPlug): ouptut channel
        """
        return HPlug(add_node(self, input_, output))

    def attribute_query(self, **kwargs):
        """Wrapper for cmds.attributeQuery command.

        Returns:
            (str list): result
        """
        return cmds.attributeQuery(self.attr, node=self.node, **kwargs)

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

    def connect(self, other, force=False, axes=None):
        """Connect this plug to another one.

        Args:
            other (str|HPlug): target for connection
            force (bool): break any existing connections
            axes (list): apply connect to list of suffixes (eg. xyz)
        """
        if axes:
            for _axis in axes:
                self.connect(str(other)+_axis, force=force)
            return
        cmds.connectAttr(self, other, force=force)

    def connect_attr(self, other, **kwargs):
        """Connect this plug to another one.

        Args:
            other (str|HPlug): target for connection
        """
        cmds.connectAttr(self, other, **kwargs)

    def delete(self):
        """Delete this attribute."""
        cmds.deleteAttr(self)

    def divide_node(self, input_, output=None):
        """Connect this plug as the first input in a divide node.

        Args:
            input_ (HPlug): second input
            output (HPlug): plug to connect output to

        Returns:
            (HPlug): ouptut channel
        """
        return HPlug(divide_node(self, input_, output))

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

    def get_val(self):
        """Get the value of this attribute.

        Returns:
            (any): attribute value
        """
        return get_val(self.name)

    def hide(self):
        """Hide this attribute in the channel box."""
        cmds.setAttr(self, keyable=False)

    def list_connections(self, **kwargs):
        """Wrapper for cmds.listConnections command.

        Returns:
            (str list): connections
        """
        return cmds.listConnections(self, **kwargs)

    def multiply_node(self, input_, output=None):
        """Connect this plug as the first input to a multiply node.

        Args:
            input_ (HPlug): second input
            output (HPlug): plug to connect output to

        Returns:
            (HPlug): output plug
        """
        return multiply_node(self, input_, output)

    def set_col(self, val):
        """Apply a colour value to this attribute.

        Args:
            val (HColor): colour value
        """
        _col = qt.get_col(val)
        cmds.setAttr(self, *_col.to_tuple(mode='float'))

    def set_enum(self, val):
        """Set value of an enum.

        Args:
            val (str): value to select
        """
        _vals = get_single(self.attribute_query(listEnum=True)).split(':')
        self.set_val(_vals.index(val))

    def set_keyframe(self, **kwargs):
        """Set keyframe on this attr."""
        cmds.setKeyframe(self, **kwargs)

    def set_val(self, val, verbose=0):
        """Set the value of this attribute.

        Args:
            val (any): attribute value
            verbose (int): print process data
        """
        set_val(self, val, verbose=verbose)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{}:"{}">'.format(type(self).__name__, self.name)
