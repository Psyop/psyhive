"""Tools for managing the base node class."""

from maya import cmds

import six

from maya_psyhive.utils import add_attr, get_unique, add_to_set
from maya_psyhive.open_maya.plug import HPlug


class BaseNode(object):
    """Base class for any node object.

    All node classes should inherit from this one.
    """

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): node name
        """
        if not isinstance(node, six.string_types):
            raise ValueError('Non-string init {} ({})'.format(
                node, type(node).__name__))
        self.node = node

    def add_attr(self, name, *args, **kwargs):
        """Add an attribute to this node.

        Args:
            name (str): attribute name

        Returns:
            (HPlug): new attribute plug
        """
        return HPlug(add_attr(self.node+'.'+name, *args, **kwargs))

    def add_to_set(self, set_):
        """Add this node to a set, creating it if required.

        Args:
            set_ (str): set to add to
        """
        add_to_set(self, set_)

    def delete(self):
        """Delete this object."""
        cmds.delete(self)

    def duplicate(self, name=None, **kwargs):
        """Duplicate this node.

        Args:
            name (str): name for duplicate

        Returns:
            (BaseNode): new node
        """
        _name = get_unique(name or self.node)
        _node = cmds.duplicate(self, name=_name, **kwargs)[0]
        return self.__class__(_node)

    def list_connections(self, **kwargs):
        """Wrapper for cmds.listConnections command.

        Returns:
            (list): connections
        """
        return cmds.listConnections(self, **kwargs)

    def plug(self, attr):
        """Get an attribute plug on this node.

        Args:
            attr (str): attribute name

        Returns:
            (HPlug): plug for attribute
        """
        if not isinstance(attr, six.string_types):
            raise ValueError('Non-string attr {} ({})'.format(
                attr, type(attr).__name__))
        return HPlug(self.node+'.'+attr)

    def __str__(self):
        return self.node

    def __repr__(self):
        return '<{}:"{}">'.format(type(self).__name__, self.node)
